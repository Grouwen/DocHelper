from fastapi import APIRouter, UploadFile, File, Depends

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