from app.entity.mysql.base import Base
from sqlalchemy import Column, Integer, String


class MysqlMainBody(Base):
    __tablename__ = "main_body"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键，自增
    file_id = Column(Integer, nullable=False) # main_body所在file的id
    body_name = Column(String(500), nullable=False) # main_body名