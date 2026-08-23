from sqlalchemy import Column, Integer, String, TEXT

from app.entity.mysql.base import Base

class MysqlChunk(Base):
    __tablename__ = "chunk"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键，自增
    file_id = Column(Integer, nullable=False) # chunk所在file的id
    title = Column(String(500), nullable=False) # chunk所在标题的标题名
    content = Column(TEXT, nullable=False) # 内容
    title_breadcrumb_path = Column(String(1000), nullable=False) # 标题结构，生成向量需要
    part = Column(Integer, nullable=False) # chunk所在标题下第几个chunk