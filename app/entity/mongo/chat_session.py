from datetime import datetime

from pydantic import BaseModel


class ChatSession(BaseModel):
    """
       chat_session
        created_at
        last_active
        message_count
        pinned
    """
    id:str|None = None
    created_at: datetime
    last_active: datetime = datetime.now()
    pinned:bool