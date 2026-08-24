# 流程入口：参数初始化、输入校验
from app.exception.hooks.node_hook import node_hook
from app.graph.states.query_state import QueryState

@node_hook
def node_entry(state:QueryState):
    """
    接收用户原始查询输入，该节点仅用于占位，后续若有需求，从此处更改
    """
    return {}