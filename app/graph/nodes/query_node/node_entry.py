# 流程入口：参数初始化、输入校验
from app.graph.hook import node_hook
from app.graph.states.query_state import QueryState

@node_hook
def node_entry(state:QueryState):
    """
    接收用户原始查询输入
    """
    user_input = state["user_input"]

    if not user_input.strip():
        return "node_generate_answer"