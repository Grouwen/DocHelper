from app.entity.mysql.base import Base
from sqlalchemy import Column, Integer, String


class MysqlFile(Base):
    __tablename__ = "file"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键，自增
    unique_name = Column(String(500), nullable=False) # uuid4编码的文件名
    origin_name = Column(String(500), nullable=False) # 用户上传的文件名