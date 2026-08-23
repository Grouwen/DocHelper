
from pymilvus import AsyncMilvusClient, DataType

from app.config.milvus_config import milvus_config

async def init_milvus_client()->AsyncMilvusClient:
    milvus_client = AsyncMilvusClient(
        uri=milvus_config.url,
        user=milvus_config.user_name,
        password=milvus_config.password,
        db_name=milvus_config.db_name,
        timeout=milvus_config.time_out,
    )

    await _ensure_collections(milvus_client)

    return milvus_client

async def close_milvus_client(milvus_client:AsyncMilvusClient):
    await milvus_client.close()


async def _ensure_collections(milvus_client:AsyncMilvusClient):
    dim=1024
    chunk_collection_name = "chunk"
    main_body_collection = "main_body"

    if not await milvus_client.has_collection(chunk_collection_name):
        await _create_chunk_collections(milvus_client,chunk_collection_name,dim)

    if not await milvus_client.has_collection(main_body_collection):
        await _create_main_body_collections(milvus_client,main_body_collection,dim)

async def _create_chunk_collections(milvus_client:AsyncMilvusClient,collection_name:str,dim:int):
    # 创建chunk collection（类似表）
    # 创建schema
    schema = milvus_client.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
    )

    # 添加字段到schema
    schema.add_field(field_name="id", datatype=DataType.INT64,is_primary=True)
    schema.add_field(field_name="file_id", datatype=DataType.INT64)
    schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
    schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

    # 3. 创建索引
    index_params = milvus_client.prepare_index_params()
    # 标量字段file_id
    index_params.add_index(
        field_name="file_id",
        index_params={"index_type": "INVERTED"},
        index_name="file_id_index"
    )
    # 稠密向量索引：HNSW + COSINE (恢复最佳性能配置)
    index_params.add_index(
        field_name="dense_vector",
        index_name="dense_vector_index",
        # HNSW (Hierarchical Navigable Small World) 是目前性能最好、最常用的基于图的索引，检索速度极快，精度极高。
        index_type="HNSW",
        # 使用 COSINE 作为稠密向量相似度计算方式
        metric_type="COSINE",
        # M: 图中每个节点的最大连接数(常用16-64)
        # efConstruction: 构建索引时的搜索范围(越大建索引越慢，但精度越高，常用100-200)
        params={"M": 16, "efConstruction": 200}
    )
    # 稀疏向量索引：专用SPARSE_INVERTED_INDEX+IP，关闭量化保证精度
    index_params.add_index(
        field_name="sparse_vector",
        index_name="sparse_vector_index",
        # 稀疏倒排索引 专门为稀疏向量（比如文本的 TF-IDF 向量、关键词权重向量，特点是大部分元素为 0，只有少数维度有值）设计的倒排索引，是稀疏向量检索的标配索引类型。
        index_type="SPARSE_INVERTED_INDEX",
        # IP（内积，Inner Product）如果向量是 “文本语义向量 + 关键词权重”，长度代表文本与主题的关联强度，此时用 IP 能同时体现 “语义匹配度” 和 “关联强度”。
        metric_type="IP",
        # DAAT_MAXSCORE 是稀疏检索的高效算法，quantization="none" 保证稀疏向量权重无损失；normalize=是否归一化。
        params={"inverted_index_algo": "DAAT_MAXSCORE", "normalize": True, "quantization": "none"}
    )

    # 创建collection
    await milvus_client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)

async def _create_main_body_collections(milvus_client:AsyncMilvusClient,collection_name:str,dim:int):
    # 创建main_body collection（类似表）
    # 创建schema
    schema = milvus_client.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
    )

    # 添加字段到schema
    schema.add_field(field_name="id", datatype=DataType.INT64,is_primary=True)
    schema.add_field(field_name="file_id", datatype=DataType.INT64)
    schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
    schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

    # 3. 创建索引
    index_params = milvus_client.prepare_index_params()
    # 稠密向量索引：HNSW + COSINE (恢复最佳性能配置)
    index_params.add_index(
        field_name="dense_vector",
        index_name="dense_vector_index",
        # HNSW (Hierarchical Navigable Small World) 是目前性能最好、最常用的基于图的索引，检索速度极快，精度极高。
        index_type="HNSW",
        # 使用 COSINE 作为稠密向量相似度计算方式
        metric_type="COSINE",
        # M: 图中每个节点的最大连接数(常用16-64)
        # efConstruction: 构建索引时的搜索范围(越大建索引越慢，但精度越高，常用100-200)
        params={"M": 16, "efConstruction": 200}
    )
    # 稀疏向量索引：专用SPARSE_INVERTED_INDEX+IP，关闭量化保证精度
    index_params.add_index(
        field_name="sparse_vector",
        index_name="sparse_vector_index",
        # 稀疏倒排索引 专门为稀疏向量（比如文本的 TF-IDF 向量、关键词权重向量，特点是大部分元素为 0，只有少数维度有值）设计的倒排索引，是稀疏向量检索的标配索引类型。
        index_type="SPARSE_INVERTED_INDEX",
        # IP（内积，Inner Product）如果向量是 “文本语义向量 + 关键词权重”，长度代表文本与主题的关联强度，此时用 IP 能同时体现 “语义匹配度” 和 “关联强度”。
        metric_type="IP",
        # DAAT_MAXSCORE 是稀疏检索的高效算法，quantization="none" 保证稀疏向量权重无损失；normalize=是否归一化。
        params={"inverted_index_algo": "DAAT_MAXSCORE", "normalize": True, "quantization": "none"}
    )

    # 创建collection
    await milvus_client.create_collection(collection_name=collection_name,schema=schema, index_params=index_params)