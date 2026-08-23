from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.domain.recall_chunk import RecallChunk
from app.domain.recall_main_body import RecallMainBody


class Retrieval(BaseModel):
    """
    retrieval: {
            original_query: "...",
            status: "success",
            rewritten_query: "...",
            flow:str,

            chunks: [
              { chunk_id, file_id, title, content },
            ],
            web_results: [
              { url, title, snippet, relevance_score }
            ],
            main_bodys: [
              { main_body_id, file_id }
            ]

            final_context: "...",
            search_latency_ms: 145,
            prompt_tokens: 1840
          },
    """
    original_query: str
    status: str
    rewritten_query: str

    chunks: List[RecallChunk] = Field(default_factory=list)
    web_results: List[RecallChunk] = Field(default_factory=list)
    main_bodys: List[RecallMainBody] = Field(default_factory=list)

    final_context: str
    search_latency_ms: float
    prompt_tokens: int


class ChatMessage(BaseModel):
    """
    chat_message 集合结构
          _id: ObjectId,
          session_id: ObjectId,
          role: "assistant",
          content: "...",
          reply_to:ObjectId,

          retrieval: {
            original_query: "...",
            status: "success",
            rewritten_query: "...",
            flow:str,

            chunks: [
              { chunk_id, file_id, title, content },
            ],
            web_results: [
              { url, title, snippet, relevance_score }
            ],
            main_bodys: [
              { main_body_id, file_id }
            ]

            final_context: "...",
            search_latency_ms: 145,
            context_tokens: 1840
          },

          created_at: ISODate,
    """
    id:str|None = None
    session_id:str
    role:str
    content: str
    reply_to: str|None
    retrieval:Retrieval|None
    output_tokens:int
    created_at:datetime = datetime.now()