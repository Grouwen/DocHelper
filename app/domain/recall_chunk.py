from pydantic import BaseModel


class RecallChunk(BaseModel):
    id: int # 为负数则代表web_search
    content: str|None = None
    distance:float
    source: str