from pathlib import Path
from pydantic_settings import SettingsConfigDict

def get_setting_config(prefix:str)->SettingsConfigDict:
    ENV_FILE_DIR = Path(__file__).resolve().parents[2] / ".env"

    return SettingsConfigDict(env_file=ENV_FILE_DIR,
                       env_file_encoding='utf-8',
                       env_prefix=prefix,
                       extra="ignore")