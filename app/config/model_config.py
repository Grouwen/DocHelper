from pydantic_settings import BaseSettings

from app.util import config_util


class LLMConfig(BaseSettings):
    llm_model: str
    llm_api_key: str
    llm_base_url: str

    model_config = config_util.get_setting_config("MODEL_")


class VMConfig(BaseSettings):
    vm_model: str
    vm_api_key: str
    vm_base_url: str

    model_config = config_util.get_setting_config("MODEL_")

class EmbeddingConfig(BaseSettings):
    file_path: str
    device:str
    bge_fp16:bool
    normalize_embeddings:bool

    model_config = config_util.get_setting_config("EMBEDDING_")

class RerankerConfig(BaseSettings):
    file_path: str
    device:str
    bge_fp16:bool

    model_config = config_util.get_setting_config("RERANKER_")

llm_config = LLMConfig()
vm_config = VMConfig()
embedding_config = EmbeddingConfig()
reranker_config = RerankerConfig()

if __name__ == '__main__':
    print(llm_config.dict())
    print(vm_config.dict())
    print(embedding_config.dict())
    print(reranker_config.dict())