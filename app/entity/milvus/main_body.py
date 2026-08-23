from typing import List, Dict
from pydantic import BaseModel

class MilvusMainBody(BaseModel):

    id: int
    file_id: int
    dense_vector: List[float]
    sparse_vector: Dict[int, float]