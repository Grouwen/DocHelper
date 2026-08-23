from tavily import AsyncTavilyClient

from app.config.tavily_config import tavily_config


def init_tavily_client()->AsyncTavilyClient:
    return AsyncTavilyClient(
        api_key=tavily_config.api_key
    )