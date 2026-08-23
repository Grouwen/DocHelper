from pydantic_settings import BaseSettings

from app.util import config_util


class MilvusConfig(BaseSettings):
    url: str
    user_name: str
    password: str
    db_name: str
    time_out: int

    model_config = config_util.get_setting_config("MILVUS_")

milvus_config = MilvusConfig()

if __name__ == '__main__':
    print(milvus_config.dict())