from pydantic_settings import BaseSettings

from app.util import config_util


class MysqlConfig(BaseSettings):
    url: str
    user_name: str
    password: str
    db_name: str

    model_config = config_util.get_setting_config("MYSQL_")

mysql_config = MysqlConfig()

if __name__ == '__main__':
    print(mysql_config.dict())