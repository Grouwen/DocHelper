import asyncio

import aiofiles
from langchain_core.prompts import PromptTemplate

from app.constants.constants import PROMPT_FILE_PATH

async def load_prompt(prompt_file_name:str,**kwargs)-> str:
    async with aiofiles.open(PROMPT_FILE_PATH / prompt_file_name, mode="r", encoding="utf-8") as f:
        prompt_content = await f.read()
    template = PromptTemplate.from_template(prompt_content,template_format="jinja2")
    return template.format(**kwargs)