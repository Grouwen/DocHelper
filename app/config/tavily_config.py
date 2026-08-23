from pydantic_settings import BaseSettings

from app.util import config_util


class TavilyConfig(BaseSettings):
    api_key: str

    model_config = config_util.get_setting_config("TAVILY_")

tavily_config = TavilyConfig()

if __name__ == '__main__':
    print(tavily_config.dict())