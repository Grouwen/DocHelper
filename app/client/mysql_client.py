from sqlalchemy.ext.asyncio.engine import create_async_engine, AsyncEngine

from app.config.mysql_config import mysql_config

def init_mysql_engine()->AsyncEngine:
    # 创建异步引擎
    db_url = f"mysql+aiomysql://{mysql_config.user_name}:{mysql_config.password}@{mysql_config.url}/{mysql_config.db_name}?charset=utf8mb4"
    engine = create_async_engine(db_url)

    return engine

async def close_mysql_engine(engine:AsyncEngine):
    await engine.dispose()