from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config.model_config import llm_config

def init_llm_model()->BaseChatModel:
    llm = init_chat_model(
        model=llm_config.llm_model,
        model_provider="openai",
        api_key=llm_config.llm_api_key,
        base_url=llm_config.llm_base_url,
        temperature=0,
        streaming=True
    )
    return llm



if __name__ == '__main__':
    llm = init_llm_model()

    print(llm.invoke("你是谁"))