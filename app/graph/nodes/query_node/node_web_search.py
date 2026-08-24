import asyncio
from typing import List

from langgraph.runtime import Runtime

from app.domain.recall_chunk import RecallChunk
from app.graph.context.query_context import QueryGraphContext
from app.exception.hooks.node_hook import node_hook
from app.graph.states.query_state import QueryState
from app.test.test_graph import test_query_node

@node_hook
async def node_web_search(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    匹配分数低/无匹配时，执行联网搜索
    """
    rewritten_query = state["rewritten_query"]
    tavily_oper = runtime.context["tavily_oper"]

    try:
        web_results = await tavily_oper.search_web(rewritten_query,limit=10)
    except Exception as e:
        return {
            "web_search_results":[]
        }

    # 转换数据格式
    web_search_results:List[RecallChunk] = []
    for result in web_results:
        web_search_results.append(RecallChunk(
            id=-1,
            content=result["content"],
            distance=result["score"],
            source="web_search"
        ))

    return {
        "web_search_results":web_search_results
    }


if __name__ == '__main__':
    result = asyncio.run(test_query_node(node_web_search,state=QueryState(
        rewritten_query="帮我看看烫金机的使用方法"
    )))["web_search_results"]

    for i in result:
        print(i)
    print(result)