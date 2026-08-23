from typing import List, Dict

from pydantic import BaseModel


class MilvusChunk(BaseModel):

    id: int
    file_id: int
    dense_vector: List[float]
    sparse_vector: Dict[int, float]