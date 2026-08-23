from typing import TypedDict
from FlagEmbedding import FlagReranker
from langchain_core.language_models import BaseChatModel

from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.mongodb_oper import MongoDBOper
from app.infrastructure.mysql_oper import MysqlOper
from app.infrastructure.tavily_oper import TavilyOper


class QueryGraphContext(TypedDict):
    embedding_oper: EmbeddingOper
    milvus_oper: MilvusOper
    mysql_oper: MysqlOper
    tavily_oper: TavilyOper
    llm_model:BaseChatModel
    reranker_model:FlagReranker