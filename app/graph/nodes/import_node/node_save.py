# 写入数据库：将向量数据持久化到Milvus将数据保存到mysql
from typing import List, Dict, Any

from langgraph.runtime import Runtime

from app.graph.context.import_context import ImportGraphContext
from app.exception.hooks.node_hook import node_hook
from app.graph.states.import_state import ImportState
from app.domain.chunk import Chunk
from app.domain.main_body import MainBody
from app.entity.milvus.chunk import MilvusChunk
from app.entity.milvus.main_body import MilvusMainBody
from app.entity.mysql.chunk import MysqlChunk
from app.entity.mysql.file import MysqlFile
from app.entity.mysql.main_body import MysqlMainBody



def _conver_to_mysql_orm(chunks:List[Chunk],main_bodys:List[MainBody])->Dict[str,Any]:
    mysql_chunks: List[MysqlChunk] = []
    for chunk in chunks:
        mysql_chunk = MysqlChunk(
            file_id=chunk.file_id,
            title=chunk.title,
            content=chunk.content,
            title_breadcrumb_path=chunk.title_breadcrumb_path,
            part=chunk.part
        )
        mysql_chunks.append(mysql_chunk)

    mysql_main_bodys: List[MysqlMainBody] = []
    for main_body in main_bodys:
        mysql_main_body = MysqlMainBody(
            file_id=main_body.file_id,
            body_name=main_body.body_name,
        )
        mysql_main_bodys.append(mysql_main_body)

    return {
        "mysql_chunks": mysql_chunks,
        "mysql_main_bodys": mysql_main_bodys,
    }

def _conver_to_milvus_orm(chunks:List[Chunk],main_bodys:List[MainBody])->Dict[str,Any]:
    milvus_chunks: List[MilvusChunk] = []
    for chunk in chunks:
        milvus_chunk = MilvusChunk(
            id=chunk.id,
            file_id=chunk.file_id,
            dense_vector=chunk.dense_vector,
            sparse_vector=chunk.sparse_vector,
        )
        milvus_chunks.append(milvus_chunk)

    milvus_main_bodys: List[MilvusMainBody] = []
    for main_body in main_bodys:
        milvus_main_body = MilvusMainBody(
            id=main_body.id,
            file_id=main_body.file_id,
            dense_vector=main_body.dense_vector,
            sparse_vector=main_body.sparse_vector,
        )
        milvus_main_bodys.append(milvus_main_body)
    return {
        "milvus_chunks": milvus_chunks,
        "milvus_main_bodys": milvus_main_bodys,
    }

@node_hook
async def node_save(state:ImportState,runtime:Runtime[ImportGraphContext]):
    """
    插入数据，先插mysql拿到id，再插入milvus保证数据一致性
    """
    milvus_oper = runtime.context["milvus_oper"]
    mysql_oper = runtime.context["mysql_oper"]

    chunks = state["chunks"]
    main_bodys = state["main_bodys"]
    origin_file_name = state["origin_file_name"]
    unique_file_name = state["unique_file_name"]

    # 1.1 将领域模型转为mysql的orm
    mysql_orm = _conver_to_mysql_orm(chunks, main_bodys)
    mysql_chunks: List[MysqlChunk] = mysql_orm["mysql_chunks"]
    mysql_main_bodys: List[MysqlMainBody]  = mysql_orm["mysql_main_bodys"]

    # 1.2 插入数据到mysql
    # 插入file对象，拿到file_id
    mysql_file = MysqlFile(
        unique_name=unique_file_name,
        origin_name=origin_file_name
    )
    await mysql_oper.save(mysql_file)
    file_id = mysql_file.id
    for chunk in mysql_chunks:
        chunk.file_id = file_id
    for main_body in mysql_main_bodys:
        main_body.file_id = file_id
    # 插入chunks和main_body
    await mysql_oper.save(mysql_chunks)
    await mysql_oper.save(mysql_main_bodys)

    # 2. 将file_id与mysql的chunk和main_body回填到领域模型，方便milvus处理
    for domain_chunk,mysql_chunk in zip(chunks,mysql_chunks):
        domain_chunk.file_id = file_id
        domain_chunk.id = mysql_chunk.id
    for domain_main_body,mysql_main_body in zip(main_bodys,mysql_main_bodys):
        domain_main_body.file_id = file_id
        domain_main_body.id = mysql_main_body.id

    # 3.1 将领域模型转为milvus的orm
    milvus_orm = _conver_to_milvus_orm(chunks, main_bodys)
    milvus_chunks: List[MilvusChunk] = milvus_orm["milvus_chunks"]
    milvus_main_bodys: List[MilvusMainBody] = milvus_orm["milvus_main_bodys"]

    # 3.2 插入数据到milvus
    await milvus_oper.save("chunk", milvus_chunks)
    # result:dict_items([('insert_count', 1), ('ids', [468436779658652745]), ('cost', 0)])
    await milvus_oper.save("main_body", milvus_main_bodys)
    # result2:dict_items([('insert_count', 18), ('ids', [468436779658652746, 468436779658652747, 468436779658652748···]), ('cost', 0)])