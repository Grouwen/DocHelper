from pydantic import BaseModel


class History(BaseModel):
    id: int
    role:str
    content:str