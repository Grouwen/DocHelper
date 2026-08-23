import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.language_models import BaseChatModel
from FlagEmbedding import FlagReranker

from app.domain.chat_request import ChatRequest
from app.domain.recall_chunk import RecallChunk
from app.entity.mongo.chat_message import ChatMessage, Retrieval
from app.entity.mongo.chat_session import ChatSession
from app.graph.context.query_context import QueryGraphContext
from app.graph.query_graph import query_app
from app.graph.states.query_state import QueryState
from app.infrastructure.embedding_oper import EmbeddingOper
from app.infrastructure.milvus_oper import MilvusOper
from app.infrastructure.mongodb_oper import MongoDBOper
from app.infrastructure.mysql_oper import MysqlOper
from app.infrastructure.tavily_oper import TavilyOper


async def _get_histories_update_last_active(mongodb_oper:MongoDBOper, chat_request: ChatRequest) -> Dict[str,Any]:
    if not chat_request.session_id:
        session = ChatSession(
            created_at=datetime.now(),
            pinned=False
        )
        session_ids = await mongodb_oper.multiterm_insert("chat_session", session)
        return {
            "session_id":session_ids[0],
            "histories":[],
        }

    if not await mongodb_oper.find_session_by_id(chat_request.session_id):
        session = ChatSession(
            created_at=datetime.now(),
            pinned=False
        )
        session_ids = await mongodb_oper.multiterm_insert("chat_session", session)
        return {
            "session_id": session_ids[0],
            "histories": [],
        }
    # 更新last_active
    await mongodb_oper.update_session_last_active(session_id=chat_request.session_id)

    histories = await mongodb_oper.find_history(session_id=chat_request.session_id)
    return {
        "session_id": chat_request.session_id,
        "histories": histories,
    }

async def _save_user_message(mongodb_oper:MongoDBOper,session_id:str, chat_request: ChatRequest)->str:
    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=chat_request.message,
        reply_to=None,
        retrieval=None,
        output_tokens=-1
    )

    user_message_ids = await mongodb_oper.multiterm_insert("chat_message",user_message)

    return user_message_ids[0]


async def _save_ai_message(user_message_id:str,session_id:str,
                           state:QueryState,mongodb_oper:MongoDBOper):
    def _limit_chunks(chunk: List[RecallChunk], limit_content_len: int = 150) -> List[RecallChunk]:
        """
        后续如果有召回显示chunk的需求时，用于限制显示chunk大小
        """
        for item in chunk:
            item.content = item.content[:limit_content_len]
        return chunk
    # 获取数据
    useful = state["useful"]
    body_names = state["body_names"]
    user_input = state["user_input"]
    graph_start_time = state["graph_start_time"]
    graph_end_time = state["graph_end_time"]
    rewritten_query = state.get("rewritten_query","")
    main_body_list = state.get("main_body_list",[])

    hyde_recall_results = state["hyde_recall_results"]
    hybrid_recall_results = state["hybrid_recall_results"]
    web_search_results = state["web_search_results"]

    final_context = state["final_context"]
    assistant_content = state["final_reply"]
    prompt_tokens = state["input_tokens"]
    output_tokens = state["output_tokens"]

    # 处理数据
    chunks = []
    chunks.extend(hyde_recall_results)
    chunks.extend(hybrid_recall_results)

    # 定义entity
    retrieval = None
    if useful or body_names:
        retrieval = Retrieval(
            original_query=user_input,
            status="success",
            rewritten_query=rewritten_query,

            chunks=chunks,
            web_results=_limit_chunks(web_search_results),
            main_bodys=main_body_list,

            final_context=final_context,
            search_latency_ms=int((graph_end_time - graph_start_time).total_seconds()),
            prompt_tokens=prompt_tokens,
        )

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        reply_to=user_message_id,
        retrieval=retrieval,
        output_tokens=output_tokens
    )

    # 保存
    await mongodb_oper.multiterm_insert("chat_message", assistant_message)



class ChatService:
    def __init__(self,embedding_oper:EmbeddingOper,milvus_oper:MilvusOper,reranker_model:FlagReranker,
                 mysql_oper:MysqlOper,llm_model:BaseChatModel,tavily_oper:TavilyOper,mongodb_oper:MongoDBOper):
        self.embedding_oper = embedding_oper
        self.milvus_oper = milvus_oper
        self.reranker_model = reranker_model
        self.mysql_oper = mysql_oper
        self.llm_model = llm_model
        self.tavily_oper = tavily_oper
        self.mongodb_oper = mongodb_oper

    async def chat(self,chat_request:ChatRequest):
        # 获取聊天记录和session_id
        histories_session_id = await _get_histories_update_last_active(self.mongodb_oper,chat_request)
        histories = histories_session_id["histories"]
        session_id = histories_session_id["session_id"]

        # 保存用户消息
        user_message_id = await _save_user_message(self.mongodb_oper,session_id,chat_request)

        state = QueryState(
            task_id=uuid.uuid4(),
            user_input=chat_request.message,
            history_list=histories,
            graph_start_time=datetime.now(),
            web_search_results=[],
            hyde_recall_results=[],
            hybrid_recall_results=[],
        )
        context = QueryGraphContext(
            embedding_oper=self.embedding_oper,
            milvus_oper=self.milvus_oper,
            mysql_oper=self.mysql_oper,
            llm_model=self.llm_model,
            reranker_model=self.reranker_model,
            tavily_oper=self.tavily_oper
        )

        final_state = await query_app.ainvoke(input=state,context=context)
        await _save_ai_message(user_message_id,session_id,final_state,self.mongodb_oper)