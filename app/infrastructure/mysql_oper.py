from typing import List

from sqlalchemy import select, Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.entity.mysql.base import Base
from app.entity.mysql.chunk import MysqlChunk
from app.entity.mysql.file import MysqlFile
from app.exception.oper_exception_hook import oper_exception_hook


class MysqlOper:
    def __init__(self, session: AsyncSession):
        self.session = session

    @oper_exception_hook("mysql")
    async def save(self,entities:Base|List[Base])->List[Base]:
        entity_list = entities if isinstance(entities, list) else [entities]
        self.session.add_all(entity_list)

        # 刷新，拿到id
        await self.session.flush()
        return entity_list

    @oper_exception_hook("mysql")
    async def query_file_by_id(self,file_ids:List[int]) -> Sequence[MysqlFile]:
        result = await self.session.execute(
            select(MysqlFile)
            .where(MysqlFile.id.in_(file_ids))
        )
        return result.scalars().all()

    @oper_exception_hook("mysql")
    async def query_chunk_by_id(self,chunk_ids:List[int]) -> Sequence[MysqlChunk]:
        result = await self.session.execute(
            select(MysqlChunk)
            .where(MysqlChunk.id.in_(chunk_ids))
        )

        return result.scalars().all()