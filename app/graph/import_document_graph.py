from langgraph.constants import END
from langgraph.graph import StateGraph

from app.graph.context.import_context import ImportGraphContext
from app.graph.nodes.import_node.node_bge_embedding import node_bge_embedding
from app.graph.nodes.import_node.node_document_split import node_document_split
from app.graph.nodes.import_node.node_entry import node_entry
from app.graph.nodes.import_node.node_save import node_save
from app.graph.nodes.import_node.node_identification_main_body import node_identification_main_body
from app.graph.nodes.import_node.node_md_img import node_md_img
from app.graph.nodes.import_node.node_pdf_to_md import node_pdf_to_md
from app.graph.states.import_state import ImportState


graph = StateGraph(state_schema=ImportState,context_schema=ImportGraphContext)

graph.add_node("node_entry", node_entry)  # 流程入口：参数初始化、输入校验
graph.add_node("node_pdf_to_md", node_pdf_to_md)  # PDF转MD：非MD格式文件的前置处理
graph.add_node("node_md_img", node_md_img)  # MD图片处理：保证文档中图片的可访问性
graph.add_node("node_document_split", node_document_split)  # 文档分块：解决大文本无法向量化/推理的问题
graph.add_node("node_identification_main_body", node_identification_main_body)  # 项目名识别：业务定制化步骤，提取核心业务标识
graph.add_node("node_bge_embedding", node_bge_embedding)  # BGE向量化：文本→向量，为Milvus存储做准备
graph.add_node("node_save", node_save)  # 向量入库：将向量数据持久化到Milvus和mysql

graph.set_entry_point("node_entry")

def route_after_entry(state:ImportState)->str:
    if state["file_type"] == "pdf":
        return "node_pdf_to_md"
    elif state["file_type"] == "md":
        return "node_md_img"
    else:
        return END

graph.add_conditional_edges("node_entry", route_after_entry,{
    "node_pdf_to_md":"node_pdf_to_md",
    "node_md_img":"node_md_img",
    END:END
})


graph.add_edge("node_pdf_to_md", "node_md_img")  # PDF转MD完成 → MD图片处理
graph.add_edge("node_md_img", "node_document_split")  # MD处理完成 → 文档分块
graph.add_edge("node_document_split", "node_identification_main_body")  # 分块完成 → 项目名识别
graph.add_edge("node_identification_main_body", "node_bge_embedding")  # 项目名识别完成 → BGE向量化
graph.add_edge("node_bge_embedding", "node_save")  # 向量化完成 → 导入Milvus向量库
graph.add_edge("node_save", END)  # 写入Milvus和Mysql → 工作流执行结束（END是内置结束节点）

import_graph_app = graph.compile()