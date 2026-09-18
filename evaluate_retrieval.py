# -*- coding: utf-8 -*-
"""
DocHelper 检索命中率评估脚本（Hit Rate@k）

用途：
  量化验证你的检索链路「主体匹配 + HyDE + 混合检索 + RRF + BGE-Reranker」
  相比「纯混合检索」到底提升了多少。

用法：
  1. 把本文件和 testset.json 一起放到 DocHelper 项目根目录
  2. 配好 .env（Milvus / MySQL / LLM / BGE-M3 / Reranker 等，和平时启动服务一致）
  3. 准备好测试集 testset.json（格式见 testset.example.json）
  4. 运行：
       python evaluate_retrieval.py --testset testset.json --topk 5

输出：
  - 逐条命中情况（baseline vs full）
  - 两条路径的 Hit Rate@k 对比（这个对比数字可以直接写进简历）

说明：
  - baseline = 直接对 query 做 BGE-M3 混合检索
  - full     = 完整查询链：指代消解 → 主体匹配 → HyDE + 混合检索 → RRF → BGE-Reranker
  - 只评估「文档内检索」，不统计 Tavily 联网结果（联网结果会虚高）
"""
import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.client.milvus_client import init_milvus_client
from app.client.mysql_client import init_mysql_engine
from app.client.tavily_client import init_tavily_client
from app.graph.context.query_context import QueryGraphContext
from app.graph.states.query_state import QueryState
from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.mysql_oper import MysqlOper
from app.infrastructure.tavily_oper import TavilyOper
from app.logr.logr import setup_logging
from app.model.embedding_model import init_embedding_model
from app.model.llm_model import init_llm_model
from app.model.reranker_model import init_reranker_model

from app.graph.nodes.query_node.node_coreference_resolution import node_coreference_resolution
from app.graph.nodes.query_node.node_mainbody_match import node_mainbody_match
from app.graph.nodes.query_node.node_hyde_match import node_hyde_match
from app.graph.nodes.query_node.node_hybrid_match import node_hybrid_match
from app.graph.nodes.query_node.node_rrf_rerank import node_rrf_rerank
from app.graph.nodes.query_node.node_bge_rerank import node_bge_rerank


def _normalize(text: str) -> str:
    """去掉所有空白，便于做子串包含判断"""
    return re.sub(r"\s+", "", text or "")


def _is_hit(contents, gold_keywords):
    """判断 top-k 召回内容里是否包含答案关键词（任一命中即算命中）"""
    if not contents:
        return False
    joined = _normalize("".join(contents))
    for kw in gold_keywords or []:
        if kw and _normalize(kw) in joined:
            return True
    return False


async def baseline_retrieve(query, embedding_oper, milvus_oper, mysql_oper, topk):
    """纯混合检索：query -> BGE-M3 双向量 -> Milvus hybrid_search -> chunk 内容"""
    vecs = await embedding_oper.aembedding_texts([query])
    dense = vecs["dense"][0]
    sparse = vecs["sparse"][0]

    reqs = milvus_oper.build_search_request(dense, sparse, limit=topk)
    results = await milvus_oper.hybrid_search("chunk", reqs, limit=topk)

    chunk_ids = [r["id"] for r in results[0]]
    chunks = await mysql_oper.query_chunk_by_id(chunk_ids)
    id_to_content = {c.id: c.content for c in chunks}
    return [id_to_content[cid] for cid in chunk_ids if cid in id_to_content]


async def full_retrieve(query, history_list, runtime, topk):
    """完整检索链（走到 BGE-Reranker 为止，不跑 generate_answer，省 LLM 生成成本）"""
    state = QueryState(user_input=query, history_list=history_list or [])

    # 1. 指代消解 + 主体提取
    r = await node_coreference_resolution(state, runtime=runtime)
    if not r.get("useful") or not r.get("body_names"):
        return None  # 被判为无用/无主体，走降级回答，不参与检索评估
    state.update(r)

    # 2. 主体匹配，锁定候选文档
    r = await node_mainbody_match(state, runtime=runtime)
    state.update(r)

    # 3. HyDE + 混合检索（文档内）
    r_hyde = await node_hyde_match(state, runtime=runtime)
    r_hybrid = await node_hybrid_match(state, runtime=runtime)
    state.update(r_hyde)
    state.update(r_hybrid)
    state["web_search_results"] = []  # 排除联网结果

    # 4. RRF 融合（同步函数）
    r = node_rrf_rerank(state)
    state.update(r)

    # 5. BGE-Reranker 精排
    r = await node_bge_rerank(state, runtime=runtime)
    return (r.get("cross_encoder_results") or [])[:topk]


async def main():
    parser = argparse.ArgumentParser(description="DocHelper 检索命中率评估")
    parser.add_argument("--testset", default="testset.json", help="测试集 JSON 路径")
    parser.add_argument("--topk", type=int, default=3, help="评估 top-k（默认 3）")
    args = parser.parse_args()

    setup_logging()

    testset_path = Path(args.testset)
    if not testset_path.exists():
        print(f"[错误] 找不到测试集文件：{testset_path}")
        sys.exit(1)

    testset = json.loads(testset_path.read_text(encoding="utf-8"))
    if not isinstance(testset, list) or not testset:
        print("[错误] 测试集应为非空 JSON 数组")
        sys.exit(1)

    # ---- 初始化依赖（和 test_query_node 一致）----
    milvus_client = await init_milvus_client()
    mysql_engine = init_mysql_engine()
    tavily_client = init_tavily_client()
    reranker_model = init_reranker_model()
    llm_model = init_llm_model()
    embedding_model = init_embedding_model()

    session_factory = async_sessionmaker(mysql_engine, expire_on_commit=False)

    base_hits = base_ok = 0
    full_hits = full_ok = 0
    rows = []

    try:
        async with session_factory.begin() as session:
            context = QueryGraphContext(
                embedding_oper=EmbeddingOper(embedding_model),
                milvus_oper=MilvusOper(milvus_client),
                mysql_oper=MysqlOper(session),
                tavily_oper=TavilyOper(tavily_client),
                llm_model=llm_model,
                reranker_model=reranker_model,
            )
            runtime = SimpleNamespace(context=context)

            for idx, item in enumerate(testset, 1):
                question = item.get("question", "")
                keywords = item.get("gold_keywords", [])
                history = item.get("history", [])
                if not question:
                    continue

                # baseline
                base_hit = base_err = False
                try:
                    base_contents = await baseline_retrieve(
                        question, context["embedding_oper"], context["milvus_oper"],
                        context["mysql_oper"], args.topk
                    )
                    base_hit = _is_hit(base_contents, keywords)
                    if base_hit:
                        base_hits += 1
                    base_ok += 1
                except Exception as e:
                    base_err = True
                    print(f"[{idx}] baseline 异常：{e}")

                # full
                full_hit = full_err = False
                try:
                    full_contents = await full_retrieve(question, history, runtime, args.topk)
                    if full_contents is None:
                        full_err = True  # 被判为无用问题，跳过
                    else:
                        full_hit = _is_hit(full_contents, keywords)
                        if full_hit:
                            full_hits += 1
                        full_ok += 1
                except Exception as e:
                    full_err = True
                    print(f"[{idx}] full 异常：{e}")

                rows.append({
                    "id": idx,
                    "question": question[:40],
                    "baseline": "命中" if base_hit else ("异常" if base_err else "未命中"),
                    "full": "命中" if full_hit else ("跳过/异常" if full_err else "未命中"),
                })

    finally:
        await milvus_client.close()
        await mysql_engine.dispose()

    # ---- 输出 ----
    print("\n" + "=" * 60)
    print(f"逐条结果（top-{args.topk}）")
    print("=" * 60)
    for r in rows:
        print(f"#{r['id']:<3} {r['question']:<40} baseline[{r['baseline']}]  full[{r['full']}]")

    base_rate = base_hits / base_ok * 100 if base_ok else 0
    full_rate = full_hits / full_ok * 100 if full_ok else 0
    print("\n" + "=" * 60)
    print(f"纯混合检索   Hit Rate@{args.topk} = {base_hits}/{base_ok} = {base_rate:.1f}%")
    print(f"完整检索链路 Hit Rate@{args.topk} = {full_hits}/{full_ok} = {full_rate:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    """
    ============================================================
逐条结果（top-3）
============================================================
#1   垂直旋转显示器需要顺时针旋转多少度？                       baseline[未命中]  full[未命中]
#2   显示器支持通过哪几种线缆连接计算机？                       baseline[命中]  full[命中]
#3   查看显示器 S/N 号有哪几种方式？                       baseline[命中]  full[命中]
#4   显示器的游戏辅助包含哪些功能？                          baseline[命中]  full[命中]
#5   显示器的护眼模式如何开启？                            baseline[命中]  full[命中]
#6   显示器的恢复出厂设置会怎样？                           baseline[命中]  full[命中]
#7   安装显示器底座支架前需要注意什么？                        baseline[命中]  full[命中]
#8   指纹电源键可以实现什么功能？                           baseline[未命中]  full[命中]
#9   充电指示灯白色常亮表示什么？                           baseline[未命中]  full[命中]
#10  如何将 F1、F2 键切换为功能键模式？                     baseline[命中]  full[命中]
#11  触摸板三指向上滑动有什么作用？                          baseline[命中]  full[命中]
#12  触摸板双指上下滑动有什么作用？                          baseline[命中]  full[命中]
#13  计算机强制关机如何操作？                             baseline[命中]  full[命中]
#14  扩展坞的 HDMI 和 VGA 接口能否同时使用？                baseline[命中]  full[命中]
#15  HUAWEI 蓝牙鼠标第二代最多支持连接几台设备？                baseline[命中]  full[命中]
#16  蓝牙鼠标的指示灯红色闪烁表示什么？                        baseline[命中]  full[命中]
#17  计算机首次开机时必须做什么？                           baseline[命中]  full[命中]
#18  笔记本如何开启护眼模式？                             baseline[命中]  full[命中]
#19  笔记本的摄像头有什么功能？                            baseline[命中]  full[命中]
#20  触摸板四指点击有什么作用？                            baseline[命中]  full[命中]
#21  开启护眼模式后屏幕会有什么变化？                         baseline[命中]  full[命中]
#22  F10 一键恢复出厂会删除什么数据？                       baseline[命中]  full[命中]
#23  F10 一键恢复出厂如何操作？                          baseline[命中]  full[命中]
#24  使用设备时应与植入医疗设备保持多少距离？                     baseline[命中]  full[命中]
#25  设备应在什么温度范围内使用？                           baseline[命中]  full[命中]
#26  它如何切换为功能键模式？                             baseline[命中]  full[命中]
#27  它最多支持连接几台蓝牙设备？                           baseline[命中]  full[命中]
#28  它的指示灯红色闪烁代表什么？                           baseline[未命中]  full[命中]
#29  它如何强制关机？                                 baseline[命中]  full[命中]
#30  它的 HDMI 和 VGA 接口能同时使用吗？                  baseline[命中]  full[命中]
#31  显示器支持通过哪些接口连接计算机？                        baseline[命中]  full[命中]
#32  笔记本触摸板支持哪些手势操作？                          baseline[命中]  full[命中]
#33  笔记本键盘快捷键包含哪些功能？                          baseline[命中]  full[命中]
#34  华为设备关于电池有哪些安全要求？                         baseline[命中]  full[命中]
#35  华为设备的环境保护要求是什么？                          baseline[未命中]  full[未命中]
#36  标准支架版显示器支持高度调节吗？                         baseline[命中]  full[命中]
#37  拆卸标准支架版显示器的支架如何操作？                       baseline[命中]  full[命中]
#38  旋转升降支架版显示器安装底座时如何操作？                     baseline[命中]  full[命中]
#39  触摸板单指双击相当于什么操作？                          baseline[命中]  full[命中]
#40  触摸板双指张开或闭合有什么作用？                         baseline[命中]  full[命中]
#41  触摸板三指向下滑动有什么作用？                          baseline[命中]  full[命中]
#42  触摸板三指左右滑动有什么作用？                          baseline[命中]  full[命中]
#43  笔记本的隐藏式环境光传感器有什么作用？                      baseline[命中]  full[命中]
#44  摄像头指示灯白色常亮表示什么？                          baseline[命中]  full[命中]
#45  笔记本键盘的 F1、F2 键默认是什么模式？                   baseline[命中]  full[命中]
#46  笔记本充电时，充电指示灯白色闪烁表示什么？                    baseline[未命中]  full[命中]
#47  给计算机充电时，关机或睡眠状态下有什么特点？                   baseline[命中]  full[命中]
#48  连接计算机到电视或投影仪需要准备什么线缆？                    baseline[命中]  full[命中]
#49  首次使用蓝牙鼠标需要完成什么？                          baseline[命中]  full[命中]
#50  蓝牙鼠标安装什么型号的电池？                           baseline[命中]  full[命中]
#51  台式机如何开启主机？                               baseline[命中]  full[命中]
#52  台式机的键盘如何切换为功能键模式？                        baseline[命中]  full[命中]
#53  清洁设备应该使用什么？                              baseline[命中]  full[命中]
#54  设备进水或有异物进入时应该怎么办？                        baseline[命中]  full[未命中]
#55  使用设备时手部不适应该怎么办？                          baseline[命中]  full[命中]
#56  雷雨天气应该注意什么？                              baseline[命中]  full[命中]
#57  使用未经认可或不兼容的电源可能有什么危险？                    baseline[命中]  full[命中]
#58  请勿让儿童或宠物对设备做什么？                          baseline[未命中]  full[命中]
#59  使用耳机时建议使用什么音量？                           baseline[命中]  full[命中]
#60  请勿将设备靠近什么热源？                             baseline[命中]  full[命中]

============================================================
纯混合检索   Hit Rate@3 = 53/60 = 88.3%
完整检索链路 Hit Rate@3 = 57/60 = 95.0%
============================================================
"""
    asyncio.run(main())