from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.middleware.cors import CORSMiddleware

from app.api.router import router
from app.client.httpx_client import init_httpx_client, close_httpx_client
from app.client.milvus_client import init_milvus_client, close_milvus_client
from app.client.minio_client import init_minio_client
from app.client.mongodb_client import init_mongodb_client, close_mongodb_client
from app.client.mysql_client import init_mysql_engine, close_mysql_engine
from app.client.tavily_client import init_tavily_client
from app.model.embedding_model import init_embedding_model
from app.model.llm_model import init_llm_model
from app.model.reranker_model import init_reranker_model
from app.model.vm_model import init_vm_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    minio_client = init_minio_client()
    httpx_client = init_httpx_client()
    milvus_client = await init_milvus_client()
    mysql_engine = init_mysql_engine()
    mongodb_client = await init_mongodb_client()
    tavily_client = init_tavily_client()

    llm_model = init_llm_model()
    vm_model = init_vm_model()
    embedding_model = init_embedding_model()
    reranker_model = init_reranker_model()

    # 挂载
    app.state.minio_client = minio_client
    app.state.httpx_client = httpx_client
    app.state.milvus_client = milvus_client
    app.state.mysql_engine = mysql_engine
    app.state.session_factory = async_sessionmaker(mysql_engine, expire_on_commit=False)
    app.state.mongodb_client = mongodb_client
    app.state.tavily_client = tavily_client
    app.state.llm_model = llm_model
    app.state.vm_model = vm_model
    app.state.embedding_model = embedding_model
    app.state.reranker_model = reranker_model

    yield

    # 清理
    await close_httpx_client(app.state.httpx_client)
    await close_milvus_client(app.state.milvus_client)
    await close_mysql_engine(app.state.mysql_engine)
    await close_mongodb_client(app.state.mongodb_client)

app = FastAPI(description="ai智能文档助手",lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议替换为具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法（包括 OPTIONS）
    allow_headers=["*"],  # 允许所有请求头
)

app.include_router(router=router)