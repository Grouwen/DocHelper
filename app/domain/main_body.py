from typing import List, Dict
from pydantic import BaseModel

class MainBody(BaseModel):

    id: int
    file_id: int
    body_name: str
    dense_vector: List[float]
    sparse_vector: Dict[int, float]