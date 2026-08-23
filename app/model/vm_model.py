from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config.model_config import vm_config

def init_vm_model()->BaseChatModel:
    vm = init_chat_model(
        model=vm_config.vm_model,
        model_provider="openai",
        api_key=vm_config.vm_api_key,
        base_url=vm_config.vm_base_url,
        temperature=0
    )

    return vm

if __name__ == '__main__':
    vm=init_vm_model()

    vm.invoke("你是谁")