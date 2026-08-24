import asyncio
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langgraph.runtime import Runtime

from app.graph.context.query_context import QueryGraphContext
from app.graph.node_hook import node_hook

from app.graph.states.query_state import QueryState
from app.test.test_graph import test_query_node
from app.util.prompt_util import load_prompt


@node_hook
async def node_coreference_resolution(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    消除指代消解，确定查询对应的 MainBody
    """
    user_input = state["user_input"]
    history_list = state["history_list"]
    llm_model = runtime.context["llm_model"]

    # 降级处理，直接回复
    try:
        # 调用大模型，获取结果
        prompt = await load_prompt("coreference_resolution.jinja2", history=history_list, user_input=user_input)
        chain = llm_model | JsonOutputParser()
        llm_resp = await chain.ainvoke(prompt)
    except Exception as e:
        return {
            "useful": False,
            "rewritten_query": "",
            "body_names": [],
        }

    # 返回结果
    useful = llm_resp["useful"]
    rewritten_query = llm_resp["rewritten_query"]
    body_names:List[str] = llm_resp["main_bodys"]

    return {
        "useful":useful,
        "rewritten_query":rewritten_query,
        "body_names":body_names,
    }



if __name__ == '__main__':
    result = asyncio.run(test_query_node(node_coreference_resolution,state=QueryState(
        user_input="你们这有烫金机吗，没有的话烫金贴也行",
        history_list=[{"role":"user","content":"苹果手机多少钱"},{"role":"assistant","content":"17w"}]
    )))
    print(result)