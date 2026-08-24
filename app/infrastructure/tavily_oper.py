import asyncio
from typing import List, Dict

from tavily import AsyncTavilyClient

from app.client.tavily_client import init_tavily_client
from app.exception.oper_exception_hook import oper_exception_hook


class TavilyOper:
    def __init__(self,tavily_client:AsyncTavilyClient):
        self.tavily_client = tavily_client

    @oper_exception_hook("tavily")
    async def search_web(self,query: str, limit: int = 10) -> List[Dict]:
        """
        Tavily 搜索，返回结构化结果
        """
        search_result = await self.tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=limit,
            include_raw_content=False,
            country="china",
            include_favicon=False,
            include_image_descriptions=False,
            include_images=False
        )
        return search_result["results"]

if __name__ == '__main__':
    tavily_client = init_tavily_client()
    oper = TavilyOper(tavily_client)
    result = asyncio.run(oper.search_web("苹果15多少钱"))

    for item in result:
        print(item)