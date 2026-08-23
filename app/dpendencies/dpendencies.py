from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.httpx_oper import HttpxOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.minio_oper import MinioOper
from app.infrastructure.mongodb_oper import MongoDBOper
from app.infrastructure.mysql_oper import MysqlOper
from app.infrastructure.tavily_oper import TavilyOper
from app.services.chat_service import ChatService
from app.services.upload_service import UploadService

async def get_httpx_oper(request: Request):
    return HttpxOper(request.app.state.httpx_client)

async def get_minio_oper(request: Request):
    return MinioOper(request.app.state.minio_client)

async def get_milvus_oper(request: Request):
    return MilvusOper(request.app.state.milvus_client)

async def get_embedding_oper(request: Request):
    return EmbeddingOper(request.app.state.embedding_model)

async def get_llm_model(request: Request):
    return request.app.state.llm_model

async def get_vm_model(request: Request):
    return request.app.state.vm_model

async def get_session(request: Request):
    session_factory = request.app.state.session_factory
    # 开启事务，保证数据一致性
    async with session_factory.begin() as session:
        yield session

async def get_mysql_oper(session: AsyncSession = Depends(get_session)):
    return MysqlOper(session)

async def get_upload_service(httpx_oper: HttpxOper = Depends(get_httpx_oper),
    minio_oper: MinioOper = Depends(get_minio_oper),
    embedding_oper: EmbeddingOper = Depends(get_embedding_oper),
    milvus_oper: MilvusOper = Depends(get_milvus_oper),
    mysql_oper: MysqlOper = Depends(get_mysql_oper),
    llm_model=Depends(get_llm_model),
    vm_model=Depends(get_vm_model)):

    return UploadService(httpx_oper, minio_oper, embedding_oper, milvus_oper,mysql_oper, llm_model, vm_model)

async def get_tavily_oper(request: Request):
    return TavilyOper(request.app.state.tavily_client)

async def get_reranker_model(request: Request):
    return request.app.state.reranker_model

async def get_mongodb_oper(request: Request):
    return MongoDBOper(request.app.state.mongodb_client)

async def get_chat_service(embedding_oper: EmbeddingOper = Depends(get_embedding_oper),
                           milvus_oper: MilvusOper = Depends(get_milvus_oper),
                           mysql_oper: MysqlOper = Depends(get_mysql_oper),
                           tavily_oper:TavilyOper = Depends(get_tavily_oper),
                           llm_model = Depends(get_llm_model),
                           reranker_model = Depends(get_reranker_model),
                           mongodb_oper = Depends(get_mongodb_oper)):
    return ChatService(embedding_oper,milvus_oper,reranker_model,mysql_oper,llm_model,tavily_oper,mongodb_oper)