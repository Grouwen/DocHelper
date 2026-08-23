import asyncio
from typing import List

from langchain_core.output_parsers import StrOutputParser
from langgraph.runtime import Runtime

from app.domain.recall_chunk import RecallChunk
from app.graph.context.query_context import QueryGraphContext
from app.graph.hook import node_hook
from app.graph.states.query_state import QueryState
from app.test.test_graph import test_query_node
from app.util.prompt_util import load_prompt

@node_hook
async def node_hyde_match(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    使用hyde拟用户回答进行match
    """
    rewritten_query = state["rewritten_query"]
    llm_model = runtime.context["llm_model"]
    embedding_oper = runtime.context["embedding_oper"]
    milvus_oper = runtime.context["milvus_oper"]

    # 查询mysql获取文件名，构建提示词
    # files:List[MysqlFile] = await mysql_oper.query_file_by_id(file_ids)
    # file_names:List[str] = []
    # for file in files:
    #     file_names.append(file.origin_name)

    # 构建提示词
    # prompt = await load_prompt("hyde.jinja2", file_names=file_names,rewritten_query=rewritten_query)
    prompt = await load_prompt("hyde.jinja2",rewritten_query=rewritten_query)

    # 调用大模型
    chain = llm_model | StrOutputParser()
    llm_resp = await chain.ainvoke(prompt)

    # 向量化用户提问
    llm_resp_vector = await embedding_oper.aembedding_texts([llm_resp])
    llm_resp_dense_vector = llm_resp_vector["dense"][0]
    llm_resp_sparse_vector = llm_resp_vector["sparse"][0]

    # 构建reqs对象，进行混合检索
    reqs = milvus_oper.build_search_request(llm_resp_dense_vector, llm_resp_sparse_vector, limit=20)
    milvus_results = await milvus_oper.hybrid_search("chunk", reqs, limit=20)

    # 转为recall_chunk
    hyde_recall_results:List[RecallChunk] = []
    for result in milvus_results[0]:
        hyde_recall_results.append(RecallChunk(
            id=result["id"],
            distance=result["distance"],
            source="hyde"
        ))


    return {
        "hyde_recall_results":hyde_recall_results
    }


if __name__ == '__main__':
    result = asyncio.run(test_query_node(node_hyde_match,state=QueryState(
        rewritten_query="迅饶网关的系统架构是什么样的",
        file_ids=[2]
    )))["hyde_recall_results"]

    for i in result:
        print(i)

    print(result)