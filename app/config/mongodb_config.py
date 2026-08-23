from pydantic_settings import BaseSettings, SettingsConfigDict

from app.util import config_util


class MongoDbConfig(BaseSettings):
    url: str
    user_name: str
    password: str
    db_name: str
    max_pool_size: int
    min_pool_size: int
    time_out_ms: int

    model_config = config_util.get_setting_config("MONGO_")

mongodb_config = MongoDbConfig()

if __name__ == '__main__':
    print(mongodb_config.dict())