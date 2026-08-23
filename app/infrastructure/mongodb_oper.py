import asyncio
from datetime import datetime
from typing import List

from bson import ObjectId
from pydantic import BaseModel
from pymongo import AsyncMongoClient

from app.client.mongodb_client import init_mongodb_client
from app.entity.mongo.chat_message import ChatMessage, Retrieval
from app.entity.mongo.chat_session import ChatSession


class MongoDBOper:
    def __init__(self,mongodb_client:AsyncMongoClient):
        self.mongodb_client = mongodb_client
        self.db = self.mongodb_client["dochelper"]

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

    async def find_history(self,session_id:str,limit:int=10):
        """
        查找聊天记录，返回最近limit条
        """
        histories = await (self.db["chat_message"].find({"session_id": session_id})
                           .sort("created_at",-1)
                           .to_list(length=limit))
        return histories

    async def find_session_by_id(self,session_id:str)->bool:
        """
        通过session_id判断是否有session记录，有返回True，没有返回False
        """
        session = await self.db["chat_session"].find_one({"_id": ObjectId(session_id)})
        if session:
            return True
        return False

    async def update_session_last_active(self,session_id:str):
        """
        通过session_id更新session最后活动时间
        """
        await self.db["chat_session"].update_one({"session_id":session_id},
                                                 {"$set":{"last_active":datetime.now()}})