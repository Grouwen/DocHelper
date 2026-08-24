# 项目名识别：业务定制化步骤，提取main_body
import re
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langgraph.runtime import Runtime

from app.graph.context.import_context import ImportGraphContext
from app.graph.node_hook import node_hook
from app.graph.states.import_state import ImportState
from app.domain.main_body import MainBody
from app.util.prompt_util import load_prompt


@node_hook
async def node_identification_main_body(state:ImportState,runtime:Runtime[ImportGraphContext]):
    # TODO:置信度过低，重做提示词，再次调用
    llm_model = runtime.context["llm_model"]
    chunks = state["chunks"]
    origin_file_name = state["origin_file_name"]
    md_content = state["md_content"]

    titles = []
    for chunk in chunks:
        titles.append(chunk.title)

    first_para = chunks[0].content

    bold_terms = list(set(re.findall(r'\*\*(.*?)\*\*', md_content)))[:10]

    prompt = await load_prompt("identification_main_body.jinja2",
                               file_name=origin_file_name,
                               titles=titles,
                               first_para=first_para,
                               bold_terms=bold_terms)
    chain = llm_model | JsonOutputParser()

    llm_resp = await chain.ainvoke(prompt)

    body_names = llm_resp["main_body"]
    confidence = llm_resp["confidence"]
    note = llm_resp["note"]

    result:List[MainBody] = []
    for body_name in body_names:
        main_body = MainBody(
            id=0,
            file_id=0,
            body_name=body_name,
            dense_vector=[],
            sparse_vector={}
        )
        result.append(main_body)


    return {
        "main_bodys":result
    }


if __name__ == '__main__':
    md_file=r"F:\PythonProjects\DocHelper\out_put\unzips\asdfsdfskldaf\full.md"