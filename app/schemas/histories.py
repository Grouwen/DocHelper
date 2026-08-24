from datetime import datetime

from pydantic import BaseModel


class History(BaseModel):
    session_id: str
    last_active: datetime
    pinned: bool