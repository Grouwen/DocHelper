from langgraph.constants import END
from langgraph.graph import StateGraph

from app.graph.context.query_context import QueryGraphContext
from app.graph.nodes.query_node.node_bge_rerank import node_bge_rerank
from app.graph.nodes.query_node.node_coreference_resolution import node_coreference_resolution
from app.graph.nodes.query_node.node_entry import node_entry
from app.graph.nodes.query_node.node_generate_answer import node_generate_answer
from app.graph.nodes.query_node.node_hybrid_match import node_hybrid_match
from app.graph.nodes.query_node.node_hyde_match import node_hyde_match
from app.graph.nodes.query_node.node_mainbody_match import node_mainbody_match
from app.graph.nodes.query_node.node_rrf_rerank import node_rrf_rerank
from app.graph.nodes.query_node.node_web_search import node_web_search
from app.graph.states.query_state import QueryState


graph = StateGraph(state_schema=QueryState,context_schema=QueryGraphContext)

graph.add_node("node_entry", node_entry)
graph.add_node("node_coreference_resolution", node_coreference_resolution)
graph.add_node("node_mainbody_match", node_mainbody_match)
graph.add_node("node_web_search", node_web_search)
graph.add_node("node_hyde_match", node_hyde_match)
graph.add_node("node_hybrid_match", node_hybrid_match)
graph.add_node("node_join", lambda x: {})  # 虚拟节点：多路搜索合并点
graph.add_node("node_rrf_rerank", node_rrf_rerank)
graph.add_node("node_bge_rerank", node_bge_rerank)
graph.add_node("node_generate_answer", node_generate_answer)

graph.set_entry_point("node_entry")

graph.add_edge("node_entry","node_coreference_resolution")

def route_to_generate_answer(state:QueryState)->str:
    if not state["useful"] or not state["body_names"]:
        return "node_generate_answer"
    else:
        return "node_mainbody_match"

graph.add_conditional_edges("node_coreference_resolution",route_to_generate_answer,{
    "node_generate_answer":"node_generate_answer",
    "node_mainbody_match":"node_mainbody_match"
})

def route_after_mainbody(state:QueryState)->list[str]:
    next_nodes = ["node_hyde_match", "node_hybrid_match"]
    if state["need_web_search"]:
        next_nodes.append("node_web_search")
    return next_nodes

graph.add_conditional_edges(
    "node_mainbody_match",
    route_after_mainbody,
    {
        "node_hyde_match": "node_hyde_match",
        "node_hybrid_match": "node_hybrid_match",
        "node_web_search": "node_web_search",
    }
)

graph.add_edge("node_web_search","node_join")
graph.add_edge("node_hyde_match","node_join")
graph.add_edge("node_hybrid_match","node_join")

graph.add_edge("node_join","node_rrf_rerank")
graph.add_edge("node_rrf_rerank","node_bge_rerank")
graph.add_edge("node_bge_rerank","node_generate_answer")
graph.add_edge("node_generate_answer",END)

query_app = graph.compile()

if __name__ == '__main__':
    print(query_app.get_graph().draw_mermaid())