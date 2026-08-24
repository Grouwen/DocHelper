from asyncio import Queue, create_task, CancelledError
from pathlib import Path
from typing import Dict, Any, List, AsyncIterator
import aiofiles
from fastapi import UploadFile, Depends
import uuid

from langchain_core.language_models import BaseChatModel

from app.constants.constants import MAX_FILE_SIZE, OUT_PUT_DOCS_PATH, ALLOWED_EXTENSIONS, MIN_FILE_SIZE
from app.graph.context.import_context import ImportGraphContext
from app.graph.import_document_graph import import_graph_app
from app.graph.states.import_state import ImportState
from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.httpx_oper import HttpxOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.minio_oper import MinioOper
from app.infrastructure.mysql_oper import MysqlOper
from app.logr.logr import get_logger
from app.util.sse_util import put_nowait, to_sse, put_critical, IMPORT_STEP_LABELS

logger = get_logger("UploadService")


async def _validate_file(file: UploadFile) -> Dict[str, Any]:
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'text/markdown',
        'text/plain'
    }

    file_name = file.filename
    if not file_name:
        raise ValueError("文件名为空")

    # 1. 校验扩展名
    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持上传 PDF 和 Markdown 文件")

    # 2. 校验 MIME 类型
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise ValueError("文件MIME类型不合法")

    # 3. 读取文件内容并校验大小
    size = 0
    content: List[bytes] = []
    while chunk := await file.read(1024 * 1024):  # 每次 1MB
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise ValueError(f"文件大小超出 {MAX_FILE_SIZE // (1024 * 1024)} MB 限制")
        content.append(chunk)

    # 读取结束后统一做下限校验
    if size == 0:
        raise ValueError("文件内容为空")
    if size < MIN_FILE_SIZE:
        raise ValueError(f"文件小于 {MIN_FILE_SIZE // 1024} KB 限制")

    # 4. 安全处理文件名（防止目录遍历攻击）
    file_path_obj = Path(file_name)
    if not file_path_obj.name:
        raise ValueError("无效的文件名")
    origin_file_name = file_path_obj.stem + file_path_obj.suffix.lower()

    # 5. 生成唯一文件名
    unique_file_name = f"{uuid.uuid4()}{ext}"

    return {
        "content": content,
        "origin_file_name": origin_file_name,
        "unique_file_name": unique_file_name
    }


async def _run_import_graph(state: ImportState, context: ImportGraphContext,
                            queue: Queue, unique_file_name: str):
    """
    后台执行 import_graph
    """
    final_state: Dict[str, Any] = dict(state)
    try:
        async for part in import_graph_app.astream(
            input=state, context=context,
            stream_mode=["updates", "values"], version="v2",
        ):
            ptype = part["type"]
            if ptype == "updates":
                for node_name in part["data"]:
                    put_nowait(queue, to_sse("step", {
                        "node": node_name,
                        "message": IMPORT_STEP_LABELS.get(node_name,node_name),
                        "status": "done",
                    }))
            elif ptype == "values":
                final_state = part["data"]

        # 汇总降级情况
        node_errors = final_state.get("node_errors", {})
        if node_errors:
            put_critical(queue, to_sse("warning", {
                "degraded_steps": [IMPORT_STEP_LABELS.get(n,n) for n in node_errors],
                "message": "部分步骤已降级处理",
            }))

        put_critical(queue, to_sse("done", {
            "unique_file_name": unique_file_name,
            "chunk_count": len(final_state.get("chunks", [])),
            "main_body_count": len(final_state.get("main_bodys", [])),
        }))
    except Exception as e:
        logger.exception(f"导入未处理异常 unique_file={unique_file_name}")
        put_critical(queue, to_sse("error", {"message": str(e)}))
    finally:
        put_critical(queue, None)

class UploadService:
    def __init__(self,httpx_oper:HttpxOper,minio_oper:MinioOper,
                 embedding_oper:EmbeddingOper,milvus_oper:MilvusOper,
                 mysql_oper:MysqlOper,llm_model:BaseChatModel,vm_model:BaseChatModel):
        self.httpx_oper = httpx_oper
        self.minio_oper = minio_oper
        self.embedding_oper = embedding_oper
        self.milvus_oper = milvus_oper
        self.mysql_oper = mysql_oper

        self.llm_model = llm_model
        self.vm_model = vm_model

    # 保留非流式上传接口
    async def upload(self, file: UploadFile):
        # 校验file
        validate_data = await _validate_file(file)
        content = validate_data["content"]
        origin_file_name = validate_data["origin_file_name"]
        unique_file_name = validate_data["unique_file_name"]

        # 保存
        full_out_put_docs_path = OUT_PUT_DOCS_PATH / Path(unique_file_name).stem
        full_out_put_docs_path.mkdir(parents=True, exist_ok=True)
        file_path = full_out_put_docs_path / unique_file_name
        async with aiofiles.open(file_path, "wb") as f:
            for chunk in content:
                await f.write(chunk)

        state = ImportState(
            task_id=str(uuid.uuid4()),
            origin_file_name=validate_data["origin_file_name"],
            local_file_path=file_path.as_posix(),
            unique_file_name=validate_data["unique_file_name"],
        )
        context = ImportGraphContext(
            httpx_oper=self.httpx_oper,
            minio_oper=self.minio_oper,
            embedding_oper=self.embedding_oper,
            milvus_oper=self.milvus_oper,
            mysql_oper=self.mysql_oper,
            llm_model=self.llm_model,
            vm_model=self.vm_model,
        )
        await import_graph_app.ainvoke(input=state, context=context)


    async def upload_stream(self,file:UploadFile) -> AsyncIterator[str]:
        """
        校验file，保存到本地，使用uuid命名
        将local_file_path，origin_file_name，unique_file_name存入到state
        origin_file_name，unique_file_name：都包含后缀
        """

        # 校验file
        validate_data= await _validate_file(file)
        content = validate_data["content"]
        origin_file_name = validate_data["origin_file_name"]
        unique_file_name = validate_data["unique_file_name"]

        # 保存
        full_out_put_docs_path = OUT_PUT_DOCS_PATH / Path(unique_file_name).stem
        full_out_put_docs_path.mkdir(parents=True, exist_ok=True)
        file_path = full_out_put_docs_path / unique_file_name
        async with aiofiles.open(file_path, "wb") as f:
            for chunk in content:
                await f.write(chunk)

        # 调用graph，解析文档
        state = ImportState(
            task_id=uuid.uuid4(),
            origin_file_name=origin_file_name,
            local_file_path=file_path.as_posix(),
            unique_file_name=unique_file_name
        )
        context = ImportGraphContext(
            httpx_oper=self.httpx_oper,
            minio_oper=self.minio_oper,
            embedding_oper=self.embedding_oper,
            milvus_oper=self.milvus_oper,
            mysql_oper=self.mysql_oper,
            llm_model=self.llm_model,
            vm_model=self.vm_model
        )

        # sse推送文件上传进度
        _background_tasks: set = set()
        queue: Queue = Queue(maxsize=4096)
        task = create_task(
            _run_import_graph(state, context, queue, validate_data["unique_file_name"])
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        yield to_sse("start", {
            "unique_file_name": validate_data["unique_file_name"],
            "origin_file_name": validate_data["origin_file_name"],
        })

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
                if item.startswith("event: done\n") or item.startswith("event: error\n"):
                    break
        except CancelledError:
            logger.info(f"客户端断开,后台继续导入 unique_file={validate_data["unique_file_name"]}")
            raise