from typing import Dict, Any, Optional
import httpx
from httpx import Response, AsyncClient

from app.logr.logr import get_logger


class HttpxOper:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def request_json(self, method: str, url: str, *,
                           headers: Optional[Dict[str, Any]] = None,
                           data: Optional[Dict[str, Any]] | bytes = None,
                           json: Optional[Dict[str, Any]] = None,
                           timeout: float = 10.0) -> Dict[str, Any]:

        try:
            request_func = getattr(self.client, method.lower())
            kwargs = {"url": url, "timeout": timeout}
            if headers is not None:
                kwargs["headers"] = headers
            if data is not None:
                kwargs["data"] = data
            if json is not None:
                kwargs["json"] = json
            response:Response = await request_func(**kwargs)

            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"远程连接失败: {url} | 状态码: {response.status_code} | 原因: {response.reason_phrase}",
                    request=response.request,
                    response=response
                )

            return response.json()

        except Exception as e:
            get_logger(__name__).error(f"HTTP请求异常: {e}")
            raise e

    async def request(self, method: str, url: str, *,
                      headers: Optional[Dict[str, Any]] = None,
                      data: Optional[Dict[str, Any]] | bytes = None,
                      json: Optional[Dict[str, Any]] = None,
                      timeout: float = 10.0) -> Response:

        try:
            request_func = getattr(self.client, method.lower())
            kwargs = {"url": url, "timeout": timeout}
            if headers is not None:
                kwargs["headers"] = headers
            if data is not None:
                kwargs["data"] = data
            if json is not None:
                kwargs["json"] = json
            response:Response = await request_func(**kwargs)

            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"远程连接失败: {url} | 状态码: {response.status_code} | 原因: {response.reason_phrase}",
                    request=response.request,
                    response=response
                )

            return response

        except Exception as e:
            get_logger(__name__).error(f"HTTP请求异常: {e}")
            raise e