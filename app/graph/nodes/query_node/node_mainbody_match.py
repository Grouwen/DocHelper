import asyncio
from typing import List, Dict

from langgraph.runtime import Runtime

from app.domain.recall_main_body import RecallMainBody
from app.graph.context.query_context import QueryGraphContext
from app.graph.node_hook import node_hook
from app.graph.states.query_state import QueryState
from app.test.test_graph import test_query_node

def need_web_search(dense_search_results:List[Dict[str, List[RecallMainBody]]],
                    spare_search_results:List[Dict[str, List[RecallMainBody]]],
                    dense_low_distance:float,
                    spare_low_distance:float)->bool:
    for dense_result in dense_search_results:
        (body_names, hits), = dense_result.items()
        if not hits:
            return True
        if hits[0].distance <= dense_low_distance:
            return True

    for spare_result in spare_search_results:
        (body_names, hits), = spare_result.items()
        if not hits:
            return True
        if hits[0].distance <= spare_low_distance:
            return True

    return False

@node_hook
async def node_mainbody_match(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    对 MainBody 混合检索 Dense + Sparse Hybrid
    返回正常与低分Mainbody 涉及到的file_id
    """
    body_names = state["body_names"]
    embedding_oper = runtime.context["embedding_oper"]
    milvus_oper = runtime.context["milvus_oper"]


    try:
        # 向量化llm提取出的main_body
        body_vectors =await embedding_oper.aembedding_texts(body_names)
        dense_vecs = body_vectors.get("dense", [])
        sparse_vecs = body_vectors.get("sparse", [])

        # 单独召回
        dense_results = await milvus_oper.search("main_body",anns_field="dense_vector",
                                           dense_vector_list=dense_vecs,output_fields=["file_id"])

        sparse_results = await milvus_oper.search("main_body", anns_field="sparse_vector",
                                                 sparse_vector_list=sparse_vecs, output_fields=["file_id"])
    except Exception as e:
        return {
            "need_web_search": True,
            "main_body_list": [],
            "file_ids": [],
        }

    # 处理结果，封装统一处理
    search_results_dense: List[Dict[str, List[RecallMainBody]]] = []
    search_results_sparse: List[Dict[str, List[RecallMainBody]]] = []
    for body_name, results in zip(body_names, dense_results):
        search_results_dense.append({body_name:[RecallMainBody(
            id=result["id"],
            file_id=result["entity"]["file_id"],
            distance=result["distance"],
        ) for result in results]})

    for body_name, results in zip(body_names, sparse_results):
        search_results_sparse.append({body_name:[RecallMainBody(
            id=result["id"],
            file_id=result["entity"]["file_id"],
            distance=result["distance"],
        ) for result in results]})

    # 判断是否需要启用web_search。当匹配的main_body分数低时，启用。用于判断用户是否问了文档内没有的内容
    start_web_search = need_web_search(search_results_dense,search_results_sparse,0.8,0.1)

    # 截断main_body，只获取dense>0.8，spare>0.1的main_body。获取file_id
    main_body_list = []
    main_body_id_list = []
    file_ids = set()
    for dense_result in search_results_dense:
        (body_names, hits), = dense_result.items()
        for hit in hits:
            if hit.distance < 0.8:
                continue
            main_body_list.append(hit)
            main_body_id_list.append(hit.id)
            file_ids.add(hit.file_id)

    for spare_result in search_results_sparse:
        (body_names, hits), = spare_result.items()
        for hit in hits:
            if hit.distance < 0.1:
                continue
            if hit.id not in main_body_id_list:
                main_body_list.append(hit)
                file_ids.add(hit.file_id)


    return {
        "need_web_search":start_web_search,
        "main_body_list":main_body_list,
        "file_ids":list(file_ids)
    }

if __name__ == '__main__':
    body_names = ["烫金机","网关","烫发棒"]

    result = asyncio.run(test_query_node(node_mainbody_match, state=QueryState(
        body_names=body_names,
    )))

    for i in result["main_body_list"]:
        print("main_body_list",i)

    print(result["need_web_search"])
    print(result["file_ids"])
    print(result["main_body_list"])