from datetime import datetime
from typing import List

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel
from pymongo import AsyncMongoClient

from app.exception.hooks.oper_exception_hook import oper_exception_hook


class MongoDBOper:
    def __init__(self,mongodb_client:AsyncMongoClient):
        self.mongodb_client = mongodb_client
        self.db = self.mongodb_client["dochelper"]

    @oper_exception_hook("mongodb")
    async def multiterm_insert(self,collection_name:str,
                               entities:List[BaseModel]|BaseModel)->List[str]:
        """
        批量查询
        """
        entity_list = entities if isinstance(entities, list) else [entities]
        insert_data = [entity.model_dump(exclude={"id"}) for entity in entity_list]

        results = await self.db[collection_name].insert_many(insert_data)
        ids = [str(result) for result in results.inserted_ids]
        return ids

    @oper_exception_hook("mongodb")
    async def find_message_by_session_id(self,session_id:str,limit:int=10):
        """
        查找聊天记录，返回最近limit条
        """
        histories = await (self.db["chat_message"].find({"session_id": session_id})
                           .sort("created_at",-1)
                           .to_list(length=limit))
        return histories

    @oper_exception_hook("mongodb")
    async def find_session_by_id(self,session_id:str)->bool:
        """
        通过session_id判断是否有session记录，有返回True，没有返回False
        """
        try:
            session_id = ObjectId(session_id)
        except InvalidId:
            return False
        session = await self.db["chat_session"].find_one({"_id": session_id})
        if session:
            return True
        return False

    @oper_exception_hook("mongodb")
    async def update_session_last_active(self,session_id:str):
        """
        通过session_id更新session最后活动时间
        """
        await self.db["chat_session"].update_one({"_id":ObjectId(session_id)},
                                                 {"$set":{"last_active":datetime.now()}})

    @oper_exception_hook("mongodb")
    async def get_history(self,limit:int=50):
        return await self.db["chat_session"].find().sort("last_active",-1).to_list(limit)