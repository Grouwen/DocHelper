import asyncio

from pymongo import AsyncMongoClient

from app.config.mongodb_config import mongodb_config


async def init_mongodb_client() -> AsyncMongoClient:
    client = AsyncMongoClient(
        f"mongodb://{mongodb_config.user_name}:{mongodb_config.password}@{mongodb_config.url}",
        maxPoolSize=mongodb_config.max_pool_size,
        minPoolSize=mongodb_config.min_pool_size,
        serverSelectionTimeoutMS=mongodb_config.time_out_ms,
    )
    # 验证连接是否可用
    await client.admin.command('ping')
    await _ensure_collection(client,mongodb_config.db_name)
    return client

async def close_mongodb_client(mongodb_client:AsyncMongoClient):
    await mongodb_client.close()

async def _ensure_collection(mongodb_client:AsyncMongoClient,db_name:str):
    # TODO:清理孤儿数据
    db = mongodb_client[db_name]
    existing = await db.list_collection_names()
    chat_message_collection = "chat_message"
    chat_session_collection = "chat_session"

    # 创建collection
    if chat_message_collection not in existing:
        await db.create_collection(chat_message_collection)
        # 为chat_message创建索引
        collection = db[chat_message_collection]
        await collection.create_index(
            [("session_id", 1), ("created_at", -1)],
            name="idx_session_created"
        )

    # 创建collection
    if chat_session_collection not in existing:
        await db.create_collection(chat_session_collection)
        # 为chat_session建立索引
        collection = db[chat_session_collection]
        await collection.create_index(
            [("last_active", -1)],
            name="idx_last_active"
        )

        await collection.create_index(
            "created_at",
            expireAfterSeconds=60 * 60 * 24 * 30,  # 30天过期
            partialFilterExpression={"pinned": False},  # 只删未置顶的
            name="idx_ttl_unpinned"
        )



if __name__ == '__main__':
    asyncio.run(init_mongodb_client())