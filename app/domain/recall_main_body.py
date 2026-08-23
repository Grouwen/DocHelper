from pydantic import BaseModel


class RecallMainBody(BaseModel):
    id: int
    file_id: int
    distance:float