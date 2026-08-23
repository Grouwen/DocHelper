# BGE向量化：文本→向量，为Milvus存储做准备
import copy

from langgraph.runtime import Runtime

from app.graph.context.import_context import ImportGraphContext
from app.graph.hook import node_hook
from app.graph.states.import_state import ImportState


@node_hook
def node_bge_embedding(state:ImportState,runtime:Runtime[ImportGraphContext]):
    """
    向量化流程：
        1.chunk
            for chunk -> f"面包屑路径：{title_breadcrumb_path}。标题：{title}。内容：{content}"
        2.main_body
            ["body1","body2"] -> body1。body2
    """

    chunks = copy.deepcopy(state["chunks"])
    main_bodys = copy.deepcopy(state["main_bodys"])
    embedding_oper = runtime.context["embedding_oper"]

    # chunk向量化，每次向量化8个
    batch_size = 8
    for batch_index in range(0, len(chunks), batch_size):
        # 浅拷贝，修改batch_chunks，chunks会改变
        batch_chunks = chunks[batch_index:batch_index+batch_size]
        embedding_list = [f"面包屑路径：{chunk.title_breadcrumb_path}。标题：{chunk.title}。内容：{chunk.content}"
                          for chunk in batch_chunks]

        print("start，all：",len(chunks),"action:",batch_size)
        embeddings = embedding_oper.embedding_texts(embedding_list)
        print("end")
        dense_vecs = embeddings.get("dense", [])
        sparse_vecs = embeddings.get("sparse", [])

        for chunk, dense_vec, sparse_vec in zip(batch_chunks, dense_vecs, sparse_vecs):
            chunk.dense_vector = dense_vec
            chunk.sparse_vector = sparse_vec

    # main_body向量化
    embedding_list = [main_body.body_name for main_body in main_bodys]
    embeddings = embedding_oper.embedding_texts(embedding_list)
    dense_vecs = embeddings.get("dense", [])
    sparse_vecs = embeddings.get("sparse", [])

    for main_body, dense_vec, sparse_vec in zip(main_bodys, dense_vecs, sparse_vecs):
        main_body.dense_vector = dense_vec
        main_body.sparse_vector = sparse_vec

    return {
        "chunks":chunks,
        "main_bodys": main_bodys
    }

if __name__ == '__main__':
    md_file = r"F:\PythonProjects\DocHelper\out_put\unzips\asdfsdfskldaf\full.md"

    with open(md_file, "r", encoding="utf-8") as file:
        md_content = file.read()