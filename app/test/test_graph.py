from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.client.httpx_client import init_httpx_client
from app.client.milvus_client import init_milvus_client
from app.client.minio_client import init_minio_client
from app.client.mysql_client import init_mysql_engine
from app.client.tavily_client import init_tavily_client
from app.graph.context.import_context import ImportGraphContext
from app.graph.context.query_context import QueryGraphContext
from app.graph.states.import_state import ImportState
from app.graph.states.query_state import QueryState
from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.httpx_oper import HttpxOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.minio_oper import MinioOper
from app.infrastructure.mysql_oper import MysqlOper
from app.infrastructure.tavily_oper import TavilyOper
from app.logr.logr import setup_logging
from app.model.embedding_model import init_embedding_model
from app.model.llm_model import init_llm_model
from app.model.reranker_model import init_reranker_model
from app.model.vm_model import init_vm_model


async def test_import_node(node_func: Callable,
                    *,
                    state:ImportState|None=None,
                    test_file_path=r"F:\PythonProjects\DocHelper\doc\2.pdf",
                    need_context=False,
                    is_async=True):
    setup_logging()

    if state is None:
        file_path = Path(test_file_path)
        state = ImportState(
        task_id="task_id",
        origin_file_name=file_path.name,
        local_file_path=str(file_path),
        file_type="",
        md_content="",
        unique_file_name=file_path.name,
        md_file_path=""
    )

    kwargs = {"state": state}
    if need_context:
        minio_client = init_minio_client()
        httpx_client = init_httpx_client()
        milvus_client = await init_milvus_client()
        mysql_engine = init_mysql_engine()

        llm_model = init_llm_model()
        vm_model = init_vm_model()
        embedding_model = init_embedding_model()
        session_factory = async_sessionmaker(mysql_engine, expire_on_commit=False)
        async with session_factory.begin() as session:

            context = ImportGraphContext(
                httpx_oper=HttpxOper(httpx_client),
                minio_oper=MinioOper(minio_client),
                llm_model=llm_model,
                vm_model=vm_model,
                milvus_oper=MilvusOper(milvus_client),
                embedding_oper=EmbeddingOper(embedding_model),
                mysql_oper=MysqlOper(session),
            )
            kwargs["runtime"] = SimpleNamespace(context=context)

    if is_async:
        return await node_func(**kwargs)
    else:
        return node_func(**kwargs)

async def test_query_node(node_func: Callable,*,
                    state:QueryState,
                    need_context=True,
                    is_async=True):
    setup_logging()

    kwargs = {"state": state}
    if need_context:
        minio_client = init_minio_client()
        httpx_client = init_httpx_client()
        milvus_client = await init_milvus_client()
        mysql_engine = init_mysql_engine()
        tavily_client = init_tavily_client()
        reranker_model = init_reranker_model()

        llm_model = init_llm_model()
        # vm_model = init_vm_model()
        embedding_model = init_embedding_model()

        session_factory = async_sessionmaker(mysql_engine, expire_on_commit=False)
        try:
            async with session_factory.begin() as session:

                context = QueryGraphContext(
                    httpx_oper=HttpxOper(httpx_client),
                    minio_oper=MinioOper(minio_client),
                    llm_model=llm_model,
                    # vm_model=vm_model,
                    milvus_oper=MilvusOper(milvus_client),
                    embedding_oper=EmbeddingOper(embedding_model),
                    mysql_oper=MysqlOper(session),
                    tavily_oper=TavilyOper(tavily_client),
                    reranker_model=reranker_model
                )
                kwargs["runtime"] = SimpleNamespace(context=context)

                if is_async:
                    return await node_func(**kwargs)
                else:
                    return node_func(**kwargs)
        finally:
            await mysql_engine.dispose()

    if is_async:
        return await node_func(**kwargs)
    else:
        return node_func(**kwargs)