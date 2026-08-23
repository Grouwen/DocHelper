from pydantic_settings import BaseSettings

from app.util import config_util


class MineruConfig(BaseSettings):
    token: str
    base_url: str

    model_config = config_util.get_setting_config("MINERU_")

mineru_config = MineruConfig()

if __name__ == '__main__':
    print(mineru_config.token)
    print(mineru_config.base_url)