import json
from asyncio import Queue, QueueFull, QueueEmpty
from typing import Any, Dict

# LangGraph 节点名 -> 面向用户的步骤描述
QUERY_STEP_LABELS: Dict[str, str] = {
    "node_entry": "初始化请求",
    "node_coreference_resolution": "指代消解与意图识别",
    "node_mainbody_match": "文档主体匹配",
    "node_hyde_match": "假设文档检索",
    "node_hybrid_match": "混合检索",
    "node_web_search": "联网搜索",
    "node_join": "多路结果合并",
    "node_rrf_rerank": "RRF 粗排",
    "node_bge_rerank": "精排重排",
    "node_generate_answer": "生成回答",
}

IMPORT_STEP_LABELS: Dict[str, str] = {
    "node_entry": "文件校验",
    "node_pdf_to_md": "PDF 解析(MinerU)",
    "node_md_img": "图片处理与上传",
    "node_document_split": "文档分块",
    "node_identification_main_body": "主体识别",
    "node_bge_embedding": "向量化",
    "node_save": "数据入库",
}

def to_sse(event: str, data: Any) -> str:
    """
    格式化为一条 SSE 事件文本。
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def put_nowait(queue: Queue, item: Any) -> None:
    """
    非阻塞入队，队列满则丢弃（仅用于非关键展示数据，保证后台流程不被卡住）。
    """
    try:
        queue.put_nowait(item)
    except QueueFull:
        pass

def put_critical(queue: Queue, item: Any) -> None:
    """
    关键事件入队（done/error/哨兵），满则淘汰最旧的一条普通事件腾出位置。
    """
    try:
        queue.put_nowait(item)
    except QueueFull:
        try:
            queue.get_nowait()
        except QueueEmpty:
            pass
        try:
            queue.put_nowait(item)
        except QueueFull:
            pass