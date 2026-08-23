from pydantic_settings import BaseSettings, SettingsConfigDict

from app.util import config_util


class MinioConfig(BaseSettings):
    endpoint: str
    access_key: str
    secret_key: str
    bucket_name: str
    img_dir: str
    secure: bool

    model_config = config_util.get_setting_config("MINIO_")

minio_config = MinioConfig()

if __name__ == '__main__':
    print(minio_config.endpoint)
    print(minio_config.access_key)
    print(minio_config.secret_key)
    print(minio_config.bucket_name)
    print(minio_config.img_dir)
    print(minio_config.secure)