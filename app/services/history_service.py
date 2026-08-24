from typing import List

from app.infrastructure.mongodb_oper import MongoDBOper
from app.schemas.histories import History
from app.schemas.result import Result


class HistoryService:
    def __init__(self,mongodb_oper:MongoDBOper):
        self.mongodb_oper = mongodb_oper

    async def get_history(self):
        history_list:List[History] = []

        histories = await self.mongodb_oper.get_history()
        for history in histories:
            history_list.append(History(
                session_id=str(history["_id"]),
                last_active=history["last_active"],
                pinned=history["pinned"],
            ))

        return Result.ok({
            "history":history_list
        })