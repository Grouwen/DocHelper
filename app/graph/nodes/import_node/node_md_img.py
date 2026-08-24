# MD图片处理：保证文档中图片的可访问性
import asyncio
import base64
import re
import shutil
import uuid
from pathlib import Path
import base64 as _base64
from typing import List, Dict

import aiofiles
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.runtime import Runtime

from app.config.minio_config import minio_config
from app.graph.context.import_context import ImportGraphContext
from app.exception.hooks.node_hook import node_hook
from app.infrastructure.minio_oper import MinioOper
from app.constants.constants import MAX_BASE64_LEN, ALLOWED_IMAGE_SUFFIX
from app.graph.states.import_state import ImportState
from app.logr.logr import get_logger
from app.infrastructure.httpx_oper import HttpxOper
from app.util.prompt_util import load_prompt
from app.util.sliding_window_util import make_sliding_window

logger = get_logger(__name__)

async def extract_images(file_type:str,
                         md_content:str,
                         md_file_path:str,
                         httpx_oper:HttpxOper)->str | None:
    if not file_type == "md":
        return None
    pattern = r'!\[([^\]]*)\]\(\s*([^\s\)]+)(?:\s+"([^"]*)")?\s*\)'
    md_images = re.findall(pattern, md_content)
    if not md_images:
        return None

    md_path = Path(md_file_path)
    out_put_images = md_path.parent / "images"
    # 清理目录
    if out_put_images.exists():
        await asyncio.to_thread(lambda: shutil.rmtree(out_put_images))
        logger.info(f"已清理旧的解压目录：{out_put_images}")

    out_put_images.mkdir(parents=True, exist_ok=True)

    for _,image_data,_ in md_images:
        if image_data.startswith("data:"):
            image_path = await _save_base64_image(b64=image_data, out_put_images_path=out_put_images)
        elif image_data.startswith("http://") or image_data.startswith("https://"):
            image_path = await _save_remote_image(image_data,out_put_images_path=out_put_images,httpx_oper=httpx_oper)
        else:
            continue

        if image_path:
            md_content = md_content.replace(image_data,image_path)

    return md_content


async def _save_base64_image(b64: str, out_put_images_path: Path, max_len=MAX_BASE64_LEN)->str | None:
    if len(b64) > max_len:
        return None
        # raise ValueError("Base64图片长度超出限制")

    # data:[mime][;base64],<data>
    try:
        header, data_part = b64.split(",", 1)
    except ValueError:
        return None
        # raise ValueError("Base64 数据格式不正确")

    if ";base64" not in header.lower():
        return None
        # raise ValueError("只支持 base64 编码的 data URI")

    mime = header.split(":", 1)[1].split(";")[0].lower() if ":" in header else ""
    if mime not in ("image/png", "image/jpeg", "image/jpg"):
        return None
        # raise ValueError(f"不支持的图片 MIME 类型: {mime}")

    ext = ".png" if mime == "image/png" else ".jpg"
    image_id = uuid.uuid4().hex
    out_path = out_put_images_path / f"{image_id}{ext}"

    decoded = _base64.b64decode(data_part, validate=True)

    async with aiofiles.open(out_path, "wb") as f:
        await f.write(decoded)

    return out_path.as_posix()

async def _save_remote_image(url: str, out_put_images_path: Path,httpx_oper:HttpxOper)->str | None:
    resp = await httpx_oper.request("get", url)

    # TODO安全防护
    content_type = resp.headers.get("content-type", "").split(";")[0].lower()
    if content_type not in ("image/png", "image/jpeg", "image/jpg"):
        return None

    ext = ".png" if content_type == "image/png" else ".jpg"
    image_id = uuid.uuid4().hex
    out_path = out_put_images_path / f"{image_id}{ext}"
    async with aiofiles.open(out_path, "wb") as f:
        await f.write(resp.content)
    return out_path.as_posix()

def scan_images(md_content:str,images_path:Path)->Dict[str,str]:
    images:Dict[str,str] = {}

    pattern = r'!\[([^\]]*)\]\(\s*([^\s\)]+)(?:\s+"([^"]*)")?\s*\)'
    md_images = re.findall(pattern, md_content)
    if not md_images:
        return images

    # 不受支持，不存在的image直接continue
    for _,md_image,_ in md_images:
        md_image_path = Path(md_image)
        if md_image_path.suffix.lower() not in ALLOWED_IMAGE_SUFFIX:
            continue
        elif not md_image_path.exists():
            absolute_path = images_path / md_image_path.name
            if not absolute_path.exists():
                continue
            else:
                images[md_image] = absolute_path.as_posix()
                continue
        images[md_image] = md_image_path.as_posix()
    return images

async def generate_summaries(md_content:str,images:Dict[str,str],
                             vm_model:BaseChatModel,char_limit=50,
                             max_rpm: int = 500)->Dict[str,str]:

    chain = vm_model | StrOutputParser()
    acquire = make_sliding_window(limit=max_rpm, window=60.0)
    # for origin_image,absolute_image in images.items():
    #     # 根据传来的scan_images获取上下文
    #     context = _get_context(origin_image, md_content, char_limit)
    #
    #     # 调用大模型获取结果
    #     base64_image = await _encode_image_to_base64(absolute_image)
    #     prompt = await load_prompt("generate_summaries.jinja2", md_content=context)
    #
    #     messages = [
    #         HumanMessage(
    #             content=[
    #                 {
    #                     "type": "text",
    #                     "text": prompt
    #                 },
    #                 {
    #                     "type": "image_url",
    #                     "image_url": {
    #                         "url": f"data:image/jpeg;base64,{base64_image}"
    #                     }
    #                 }
    #             ]
    #         )
    #     ]
    #     summary = await chain.ainvoke(messages)
    #     image_summaries[origin_image] = summary
    #     logger.info(f"生成画面分析：{origin_image}:{summary}")
    #     await asyncio.sleep(2)
    async def _summarize_one(origin_image: str, absolute_image: str) -> tuple[str, str]:
        await acquire()  # ← 限流点：超限自动排队

        context = _get_context(origin_image, md_content, char_limit)
        base64_image = await _encode_image_to_base64(absolute_image)
        prompt = await load_prompt("generate_summaries.jinja2", md_content=context)

        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ]
            )
        ]
        summary = await chain.ainvoke(messages)
        logger.info(f"生成画面分析：{origin_image}:{summary}")
        return origin_image, summary

    tasks = [
        _summarize_one(origin_image, absolute_image)
        for origin_image, absolute_image in images.items()
    ]
    results = await asyncio.gather(*tasks)

    return dict(results)

def _get_context(image:str,md_content:str,char_limit=50)->List[str]:
    context: List[str] = []

    # 对 URL 进行正则转义，防止特殊字符报错
    image_url = image.strip()
    escaped_url = re.escape(image_url)

    # 匹配正则
    pattern = re.compile(r'!\[[^\]]*\]\(' + escaped_url + r'[^)]*\)', re.DOTALL)
    match = pattern.search(md_content)
    if not match:
        return []
    start, end = match.span()

    # 提取上文：从当前图片起点往前截取
    prev_start = max(0, start - char_limit)
    context_before = md_content[prev_start:start].strip()
    context.append(context_before)

    # 提取下文：从当前图片终点往后截取
    next_end = min(len(md_content), end + char_limit)
    context_after = md_content[end:next_end].strip()
    context.append(context_after)

    return context

async def _encode_image_to_base64(image_path:str)->str:
    async with aiofiles.open(image_path, "rb") as img_file:
        base64_str = base64.b64encode(await img_file.read()).decode("utf-8")
    return base64_str

def rewrite_md_content(md_content:str,*,
                       image_summaries:Dict[str,str]|None = None,
                       image_urls:Dict[str,str]|None = None)->str:
    target_dict:Dict[str,Dict[str,str]] = {}
    if image_summaries:
        for image,summary in image_summaries.items():
            target_dict.setdefault(image, {})["summary"] = summary
    if image_urls:
        for image,url in image_urls.items():
            target_dict.setdefault(image, {})["url"] = url
    for image, image_des in target_dict.items():
        alt_replacement = image_des.get("summary")
        url_replacement = image_des.get("url")

        pattern = re.compile(r'!\[([^\]]*)\]\(\s*([^\s\)]+)(?:\s+"([^"]*)")?\s*\)')

        def _repl(m):
            orig_alt, orig_url, orig_title = m.group(1), m.group(2), m.group(3)
            # 仅当 URL 精确匹配时才替换
            if orig_url != image:
                return m.group(0)
            new_alt = alt_replacement if alt_replacement else orig_alt
            new_url = url_replacement if url_replacement else orig_url
            if orig_title is not None:
                return f'![{new_alt}]({new_url} "{orig_title}")'
            return f'![{new_alt}]({new_url})'

        md_content = pattern.sub(_repl, md_content)
    return md_content


async def upload_image_to_minio(unique_file_name, images:Dict[str, str],minio_oper:MinioOper)->Dict[str,str]:
    unique_file_name_path = Path(unique_file_name)

    upload_dir = minio_config.img_dir+ "/" +unique_file_name_path.stem

    # 上传之前先清理，必须去除"/"否则查不到
    await minio_oper.remove_dir(upload_dir[1:])

    # 上传
    upload_image_url:Dict[str,str] = {}
    for origin_image,absolute_image in images.items():
        object_name =  upload_dir+ "/" + Path(absolute_image).name

        await minio_oper.upload(
            object_name=object_name,
            file_path=absolute_image,
        )
        upload_image_url[origin_image] = minio_config.endpoint+"/"+minio_config.bucket_name+object_name
    return upload_image_url

@node_hook
async def node_md_img(state:ImportState,runtime:Runtime[ImportGraphContext]):
    httpx_oper: HttpxOper = runtime.context["httpx_oper"]
    minio_oper: MinioOper = runtime.context["minio_oper"]
    vm_model: BaseChatModel = runtime.context["vm_model"]

    # 读取md内容
    md_file_path = state["md_file_path"]
    async with aiofiles.open(md_file_path, mode="r", encoding="utf-8") as f:
        md_content = await f.read()

    # 提取用户上传的md文件中的图片，保存到本地，并更新md_content中的图片路径
    processed_md_content = await extract_images(state["file_type"], md_content,md_file_path, httpx_oper)
    if processed_md_content is not None:
        md_content = processed_md_content

    # 有的md中的图片不会使用，筛选出使用的图片，并将md文件中的相对路径转为绝对路径保存
    images = scan_images(md_content,Path(md_file_path).parent/"images")

    try:
        # 调用大模型生成图片的描述信息
        image_summaries = await generate_summaries(md_content, images,vm_model)

        # 回填alt到md_content
        md_content = rewrite_md_content(md_content,image_summaries=image_summaries)

        # 上传图片到minio
        upload_image_url = await upload_image_to_minio(state["unique_file_name"], images, minio_oper)

        # 回填url到md_content
        md_content = rewrite_md_content(md_content, image_urls=upload_image_url)

        # 保存到本地以_new.md命名
        save_path = Path(str(md_file_path).replace(Path(md_file_path).suffix, "_new.md"))
        async with aiofiles.open(save_path, mode="w", encoding="utf-8") as f:
            await f.write(md_content)

        return {
            "md_content":md_content,
            "md_file_path":save_path
        }
    except Exception as e:
        return {
            "md_content":md_content,
            "md_file_path":md_file_path
        }


if __name__ == '__main__':
    pass