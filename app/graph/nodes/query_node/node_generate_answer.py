import time
from datetime import datetime
from typing import List, Dict, Any

from langchain_core.language_models import BaseChatModel
from langgraph.runtime import Runtime

from app.domain.recall_chunk import RecallChunk
from app.entity.mongo.chat_message import ChatMessage, Retrieval
from app.graph.context.query_context import QueryGraphContext
from app.graph.hook import node_hook
from app.graph.states.query_state import QueryState
from app.infrastructure.mongodb_oper import MongoDBOper
from app.util.prompt_util import load_prompt

async def ask_llm_get_metadata(llm:BaseChatModel,prompt:str)->Dict[str,Any]:
    final_reply = ""
    usage_metadata = {}
    async for chunk in llm.astream(prompt):
        if chunk.content:
            final_reply += chunk.content
        if chunk.usage_metadata:
            usage_metadata = chunk.usage_metadata
    return {
        "final_context": prompt,
        "final_reply": final_reply,
        "input_tokens": usage_metadata["input_tokens"],
        "output_tokens": usage_metadata["output_tokens"],
        "graph_end_time": datetime.now()
    }

@node_hook
async def node_generate_answer(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    生成 Prompt 并调用 LLM 生成最终回答
    """
    useful = state["useful"]
    body_names = state["body_names"]
    user_input = state["user_input"]
    cross_encoder_results = state.get("cross_encoder_results",[])
    rewritten_query = state["rewritten_query"]
    llm_model = runtime.context["llm_model"]

    # 判断useful
    if not useful or not body_names:
        prompt = await load_prompt("unuseful_answer.jinja2",user_input=user_input)
        return await ask_llm_get_metadata(llm_model, prompt)

    # 处理提示词
    context = "\n".join(f"文档{index}：{result}" for index, result in enumerate(cross_encoder_results, start=1))
    # 加载提示词
    prompt = await load_prompt("generate_answer.jinja2",
                      context=context,rewritten_query=rewritten_query)
    return await ask_llm_get_metadata(llm_model,prompt)