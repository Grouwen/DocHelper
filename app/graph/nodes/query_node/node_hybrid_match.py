import asyncio
from typing import List

from langgraph.runtime import Runtime

from app.domain.recall_chunk import RecallChunk
from app.graph.context.query_context import QueryGraphContext
from app.graph.node_hook import node_hook
from app.graph.states.query_state import QueryState
from app.test.test_graph import test_query_node

@node_hook
async def node_hybrid_match(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    锁定候选 Chunk 池，在候选池内执行普通混合检索
    """
    file_ids = state["file_ids"]
    rewritten_query = state["rewritten_query"]
    embedding_oper = runtime.context["embedding_oper"]
    milvus_oper = runtime.context["milvus_oper"]

    try:
        # 如果file_ids为空，则降级从所有文件中匹配
        filter = ""
        if file_ids:
            filter = f'file_id in {file_ids}'

        # 向量化用户提问
        body_vectors =await embedding_oper.aembedding_texts([rewritten_query])
        dense_vec = body_vectors.get("dense", [])[0]
        sparse_vec = body_vectors.get("sparse", [])[0]

        # 构建search_request对象，进行向量检索
        reqs = milvus_oper.build_search_request(dense_vec, sparse_vec)
        milvus_results = await milvus_oper.hybrid_search("chunk", reqs,
                                                  filter=filter,limit=20)
    except Exception as e:
        return {
            "hybrid_recall_results": []
        }

    # 转为recall_chunk
    hybrid_recall_results: List[RecallChunk] = []
    for result in milvus_results[0]:
        hybrid_recall_results.append(RecallChunk(
            id=result["id"],
            distance=result["distance"],
            source="hybrid"
        ))

    return {
        "hybrid_recall_results": hybrid_recall_results
    }


if __name__ == '__main__':
    result = asyncio.run(test_query_node(node_hybrid_match,state=QueryState(
        file_ids=[2],
        rewritten_query="迅饶网关的系统架构是什么样的"
    )))["hybrid_recall_results"]

    for i in result:
        print(i)
    print(result)