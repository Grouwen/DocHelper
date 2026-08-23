from typing import TypedDict

from langchain_core.language_models import BaseChatModel

from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.minio_oper import MinioOper
from app.infrastructure.httpx_oper import HttpxOper
from app.infrastructure.mysql_oper import MysqlOper


class ImportGraphContext(TypedDict):
    httpx_oper: HttpxOper
    minio_oper: MinioOper
    embedding_oper: EmbeddingOper
    milvus_oper: MilvusOper
    mysql_oper: MysqlOper

    llm_model:BaseChatModel
    vm_model:BaseChatModel