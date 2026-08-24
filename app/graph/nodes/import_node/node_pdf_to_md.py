# PDF转MD：非MD格式文件的前置处理
import asyncio
import shutil
import time
import zipfile
from pathlib import Path
from typing import Dict, Any

import aiofiles
from httpx import Response
from langgraph.runtime import Runtime

from app.config.mineru_config import mineru_config
from app.constants.constants import OUT_PUT_ZIPS_PATH, OUT_PUT_UNZIPS_PATH
from app.graph.context.import_context import ImportGraphContext
from app.exception.hooks.node_hook import node_hook
from app.graph.states.import_state import ImportState
from app.logr.logr import get_logger
from app.infrastructure.httpx_oper import HttpxOper
from app.test.test_graph import test_import_node

logger = get_logger(__name__)

async def upload_and_poll(local_file_path:str,httpx_oper:HttpxOper)->str:
    # 1.获取上传链接
    mineru_url = f"{mineru_config.base_url}/file-urls/batch"
    request_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {mineru_config.token}"
    }
    mineru_data = {
        "files": [{"name": "demo.pdf"}],
        "model_version": "vlm"
    }

    resp_json:Dict[str,Any] = await httpx_oper.request_json("post",mineru_url, headers=request_headers, json=mineru_data)
    if resp_json["code"] != 0:
        raise RuntimeError(f"[获取上传链接] API业务错误，返回数据：{resp_json}")

    # 提取核心数据：上传链接和任务唯一标识
    signed_url = resp_json["data"]["file_urls"][0]
    batch_id = resp_json["data"]["batch_id"]
    logger.info(f"batch_id：{batch_id}，上传链接已生成")

    # 2.读取PDF二进制数据，准备上传
    async with aiofiles.open(local_file_path, mode="rb") as f:
        file_data = await f.read()

    # 3.上传文件
    await httpx_oper.request("put",signed_url, data=file_data)

    # 4.根据batch_id轮询任务状态，直至完成/失败/超时
    poll_url = f"{mineru_config.base_url}/extract-results/batch/{batch_id}"
    start_time = time.time()
    timeout_seconds = 600  # 最大超时时间10分钟（适配600页内PDF）
    poll_interval = 3  # 轮询间隔3秒（平衡查询频率和服务端压力）
    logger.info(f"开始监控任务状态，batch_id：{batch_id}，最大超时：{timeout_seconds}s")

    while True:
        # 超时检查：超过最大时间直接终止轮询
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            raise TimeoutError(f"[任务轮询] 超时！任务处理超{int(timeout_seconds)}秒，batch_id：{batch_id}")

        # 发起轮询查询，短超时10秒，异常则重试
        try:
            poll_resp:Response = await httpx_oper.request("get",url=poll_url, headers=request_headers, timeout=10)
        except Exception as e:
            logger.warning(f"[任务轮询] 网络请求异常，{poll_interval}秒后重试：{str(e)}")
            await asyncio.sleep(poll_interval)
            continue

        # 处理HTTP响应错误：5xx服务端繁忙则重试，其他错误直接抛出
        if poll_resp.status_code != 200:
            if 500 <= poll_resp.status_code < 600:
                logger.warning(f"[任务轮询] 服务端繁忙（状态码：{poll_resp.status_code}），{poll_interval}秒后重试")
                await asyncio.sleep(poll_interval)
                continue
            else:
                raise RuntimeError(
                    f"[任务轮询] HTTP请求失败，状态码：{poll_resp.status_code}，响应内容：{poll_resp.text}")

        # 解析轮询结果，校验业务状态
        poll_data = poll_resp.json()
        if poll_data["code"] != 0:
            raise RuntimeError(f"[任务轮询] API业务错误，返回数据：{poll_data}")

        extract_results = poll_data["data"]["extract_result"]
        # 结果暂空，继续轮询
        if not extract_results:
            logger.debug(f"[任务轮询] 结果暂为空，已耗时{int(elapsed_time)}s，继续等待")
            await asyncio.sleep(poll_interval)
            continue

        # 解析任务状态，分支处理
        result_item = extract_results[0]
        state_status = result_item["state"]
        # 状态1：任务完成，提取ZIP下载链接
        if state_status == "done":
            logger.info(f"[任务轮询] 解析任务完成！总耗时：{int(elapsed_time)}s，batch_id：{batch_id}")
            full_zip_url = result_item.get("full_zip_url")
            if not full_zip_url:
                raise RuntimeError(f"[任务轮询] 任务完成但未返回ZIP包下载链接，batch_id：{batch_id}")
            logger.info(f"[任务轮询] 结果ZIP包下载链接：{full_zip_url}...")
            return full_zip_url
        # 状态2：任务失败，提取错误信息抛出
        elif state_status == "failed":
            err_msg = result_item.get("err_msg", "未知错误，无具体信息")
            raise RuntimeError(f"[任务轮询] 解析任务失败，batch_id：{batch_id}，错误信息：{err_msg}")
        # 状态3：处理中，实时打印进度（覆盖当前行）
        else:
            logger.debug(f"[任务轮询] 处理中（已耗时{int(elapsed_time)}s），状态：{state_status} | 刷新间隔{poll_interval}s",)
            await asyncio.sleep(poll_interval)


async def download_and_extract(zip_url:str,
                               httpx_oper:HttpxOper,
                               zip_download_path:Path,
                               unzip_path:Path,
                               unique_file_name:str)->Path:
    # 去后缀，方便后续操作
    unique_file_name = Path(unique_file_name).stem
    # 下载zip文件
    resp = await httpx_oper.request("get", zip_url)
    zip_full_path = zip_download_path / f"{unique_file_name}.zip"
    zip_download_path.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(zip_full_path, mode="wb") as f:
        await f.write(resp.content)

    # 解压（若存在这个目录，则清空）
    unzip_full_path = unzip_path / unique_file_name
    if unzip_full_path.exists():
        try:
            # 递归删除整个目录树，包括目录本身及其所有子目录和文件。
            await asyncio.to_thread(lambda: shutil.rmtree(unzip_full_path))
            logger.info(f"已清理旧的解压目录：{unzip_full_path}")
        except Exception as e:
            logger.warning(f"清理旧目录失败，可能不影响新文件解压：{str(e)}")

    unzip_full_path.mkdir(parents=True, exist_ok=True)
    def unzip():
        with zipfile.ZipFile(zip_full_path, 'r') as zip_file_obj:
            zip_file_obj.extractall(unzip_full_path)
    await asyncio.to_thread(unzip)

    # 递归查找解压目录下所有MD文件
    md_file_list = list(unzip_full_path.rglob("*.md"))
    if not md_file_list:
        raise FileNotFoundError(f"解压目录中未找到任何.md格式文件：{unzip_full_path}")

    # 获取md文件的本地地址，同名>full.md>兜底（拿第一个）
    for md_file in md_file_list:
        if md_file.stem == unique_file_name:
            return md_file.resolve()
    for md_file in md_file_list:
        if md_file.stem == "full":
            return md_file.resolve()
    return md_file_list[0]


@node_hook
async def node_pdf_to_md(state:ImportState,runtime:Runtime[ImportGraphContext]):
    httpx_oper: HttpxOper = runtime.context["httpx_oper"]
    local_file_path = state["local_file_path"]
    unique_file_name = state["unique_file_name"]

    # 上传并拿到zip_url
    zip_url = await upload_and_poll(local_file_path, httpx_oper)

    # 下载MinerU解析结果ZIP包并解压，提取目标MD文件
    md_file_path = await download_and_extract(zip_url, httpx_oper, OUT_PUT_ZIPS_PATH, OUT_PUT_UNZIPS_PATH,
                                              unique_file_name=unique_file_name)
    return {
        "md_file_path": md_file_path
    }


if __name__ == '__main__':
    result = asyncio.run(test_import_node(node_pdf_to_md,state=ImportState(
        local_file_path=r"F:\PythonProjects\DocHelper\doc\迅饶网关与小米产品通讯配置说明.pdf",
        unique_file_name="asebdeasdf",
    ),need_context=True))["md_file_path"]

    print(result)