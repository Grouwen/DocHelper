from typing import List, Dict

from pydantic import BaseModel


class Chunk(BaseModel):

    id: int  # chunk id
    file_id: int  # chunk对应的file id
    title: str  # chunk所在标题的标题名
    content: str  # 内容
    title_breadcrumb_path: str  # 标题结构，生成向量需要
    part: int  # chunk所在标题下第几个chunk
    dense_vector: List[float]  # 稠密向量
    sparse_vector: Dict[int, float]  # 稀疏向量