from fastapi import APIRouter, UploadFile, File, Depends
from starlette.responses import StreamingResponse

from app.domain.chat_request import ChatRequest
from app.dpendencies.dpendencies import get_upload_service, get_chat_service
from app.services.chat_service import ChatService
from app.services.upload_service import UploadService

router = APIRouter()

@router.post("/api/upload")
async def upload(file:UploadFile = File(...),
                 upload_service: UploadService = Depends(get_upload_service)):
    return await upload_service.upload(file)

@router.post("/api/chat/send")
async def chat(chat_request: ChatRequest,
               chat_service:ChatService = Depends(get_chat_service)):
    return await chat_service.chat(chat_request)

@router.post("/api/chat/stream")
async def chat(chat_request: ChatRequest,
               chat_service: ChatService = Depends(get_chat_service)):
    return StreamingResponse(
        chat_service.chat_stream(chat_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # 关闭 nginx 代理缓冲，保证实时推送
        },
    )