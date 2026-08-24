from typing import List, Any, Dict, Tuple

from pydantic import BaseModel
from pymilvus import AsyncMilvusClient, AnnSearchRequest, WeightedRanker, RRFRanker

from app.exception.oper_exception_hook import oper_exception_hook


class MilvusOper:
    def __init__(self, milvus_client: AsyncMilvusClient):
        self.milvus_client = milvus_client

    @oper_exception_hook("milvus")
    async def save(self, collection_name: str,
                   entities: BaseModel | List[BaseModel],
                   auto_id: bool = False,
                   primary_key_field: str = "id") -> dict:
        """
        :param collection_name: collection名字
        :param entities: 保存的数据
        :param auto_id: 主键是否由milvus维护
        :param primary_key_field: 主键名（当auto_id为True时，必填）
        :return:
        """

        entity_list = entities if isinstance(entities, list) else [entities]

        insert_data = [entity.model_dump() for entity in entity_list]

        if auto_id:
            for record in insert_data:
                record.pop(primary_key_field, None)

        res = await self.milvus_client.insert(collection_name=collection_name, data=insert_data)

        return res

    @oper_exception_hook("milvus")
    async def hybrid_search(self, collection_name: str,
                            reqs: List[AnnSearchRequest],
                            ranker_weights: Tuple[float, float] = (0.8, 0.2),
                            norm_score: bool = True, limit=10,
                            output_fields: List[str] | None = None,
                            filter: str = "") -> List[List[dict]]:
        # 仅能查询单条
        rerank = WeightedRanker(ranker_weights[0], ranker_weights[1], norm_score=norm_score)

        res = await self.milvus_client.hybrid_search(
            collection_name=collection_name,
            reqs=reqs,
            ranker=rerank,
            limit=limit,
            output_fields=output_fields,
            filter=filter
        )

        return res

    @oper_exception_hook("milvus")
    async def search(self, collection_name: str,
                     anns_field: str,
                     dense_vector_list:List[List[float]]|None = None,
                     sparse_vector_list:List[Dict[int,float]]|None=None,
                     dense_params: Dict[str, str] | None = None,
                     sparse_params: Dict[str, str] | None = None,
                     limit=5,
                     output_fields: List[str] | None = None,
                     filter: str = "") -> List[List[dict]]:
        if dense_vector_list and sparse_vector_list:
            raise ValueError("search仅支持查询1个向量")

        if not dense_params and dense_vector_list:
            dense_params = {"metric_type": "COSINE"}

        if not sparse_params and sparse_vector_list:
            sparse_params = {"metric_type": "IP"}

        res = await self.milvus_client.search(
            collection_name=collection_name,
            data=dense_vector_list or sparse_vector_list,
            anns_field=anns_field,
            limit=limit,
            search_params=dense_params or sparse_params,
            output_fields=output_fields,
            filter=filter
        )

        return res

    def build_search_request(self, dense_vector: List[float], sparse_vector: Dict[int, float],
                             dense_params: Dict[str, str] | None = None,
                             sparse_params: Dict[str, str] | None = None,
                             expr: str = "", limit: int = 10) -> List[AnnSearchRequest]:
        if not dense_params:
            dense_params = {"metric_type": "COSINE"}
        if not sparse_params:
            sparse_params = {"metric_type": "IP"}

        dense_req = AnnSearchRequest(
            data=[dense_vector],
            anns_field="dense_vector",
            param=dense_params,
            expr=expr,
            limit=limit
        )

        sparse_req = AnnSearchRequest(
            data=[sparse_vector],
            anns_field="sparse_vector",
            param=sparse_params,
            expr=expr,
            limit=limit
        )

        return [dense_req, sparse_req]
