from pydantic_settings import BaseSettings, SettingsConfigDict

from app.util import config_util


class WebConfig(BaseSettings):
    host: str
    port: int

    model_config = config_util.get_setting_config("WEB_")

web_config = WebConfig()

if __name__ == '__main__':
    print(web_config.host)
    print(web_config.port)