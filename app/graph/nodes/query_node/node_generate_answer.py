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
    ai_message = await llm.ainvoke(prompt)
    return {
        "assistant_content": ai_message.content,
        "prompt_tokens": ai_message.usage_metadata["input_tokens"],
        "output_tokens": ai_message.usage_metadata["output_tokens"]
    }


async def save_to_mongodb(state:QueryState,mongodb_oper:MongoDBOper,
                          final_context:str,
                          reply:Dict[str,Any],no_retrieval:bool=False):
    # 获取数据
    user_message_id = state["user_message_id"]
    session_id = state["session_id"]
    user_input = state["user_input"]
    graph_start_time = state["graph_start_time"]
    rewritten_query = state.get("rewritten_query","")
    main_body_list = state.get("main_body_list",[])

    hyde_recall_results = state["hyde_recall_results"]
    hybrid_recall_results = state["hybrid_recall_results"]
    web_search_results = state["web_search_results"]

    assistant_content = reply["assistant_content"]
    prompt_tokens = reply["prompt_tokens"]
    output_tokens = reply["output_tokens"]

    # 处理数据
    chunks = []
    chunks.extend(hyde_recall_results)
    chunks.extend(hybrid_recall_results)

    # 定义entity
    if not no_retrieval:
        retrieval = Retrieval(
            original_query=user_input,
            status="success",
            rewritten_query=rewritten_query,

            chunks=chunks,
            web_results=_limit_chunks(web_search_results),
            main_bodys=main_body_list,

            final_context=final_context,
            search_latency_ms=int((datetime.now() - graph_start_time).total_seconds()),
            prompt_tokens=prompt_tokens,
        )

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        reply_to=user_message_id,
        retrieval=retrieval if not no_retrieval else None,
        output_tokens=output_tokens
    )

    # 保存
    await mongodb_oper.multiterm_insert("chat_message", assistant_message)

def _limit_chunks(chunk:List[RecallChunk],limit_content_len:int=150)->List[RecallChunk]:
    """
    后续如果有召回显示chunk的需求时，用于限制显示chunk大小
    """
    for item in chunk:
        item.content = item.content[:limit_content_len]
    return chunk

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
    mongodb_oper = runtime.context["mongodb_oper"]

    # 判断useful
    if not useful or not body_names:
        prompt = await load_prompt("unuseful_answer.jinja2",user_input=user_input)
        reply = await ask_llm_get_metadata(llm_model, prompt)
        await save_to_mongodb(state,mongodb_oper,"",reply,no_retrieval=True)
        return {
            "reply": reply["assistant_content"]
        }


    # 处理提示词
    context = "\n".join(f"文档{index}：{result}" for index, result in enumerate(cross_encoder_results, start=1))
    # 加载提示词
    prompt = await load_prompt("generate_answer.jinja2",
                      context=context,rewritten_query=rewritten_query)
    reply = await ask_llm_get_metadata(llm_model,prompt)
    # 保存数据
    await save_to_mongodb(state,mongodb_oper,context,reply)

    return {
        "reply":reply["assistant_content"]
    }