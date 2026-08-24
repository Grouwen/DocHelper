from typing import Dict, Any, Optional
import httpx
from httpx import Response, AsyncClient

from app.exception.hooks.oper_exception_hook import oper_exception_hook


class HttpxOper:
    def __init__(self, client: AsyncClient):
        self.client = client

    @oper_exception_hook("httpx")
    async def request_json(self, method: str, url: str, *,
                           headers: Optional[Dict[str, Any]] = None,
                           data: Optional[Dict[str, Any]] | bytes = None,
                           json: Optional[Dict[str, Any]] = None,
                           timeout: float = 10.0) -> Dict[str, Any]:

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

    @oper_exception_hook("httpx")
    async def request(self, method: str, url: str, *,
                      headers: Optional[Dict[str, Any]] = None,
                      data: Optional[Dict[str, Any]] | bytes = None,
                      json: Optional[Dict[str, Any]] = None,
                      timeout: float = 10.0) -> Response:


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