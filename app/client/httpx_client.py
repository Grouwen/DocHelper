from httpx import AsyncClient

def init_httpx_client()->AsyncClient:
    return AsyncClient()


async def close_httpx_client(httpx_client:AsyncClient):
    await httpx_client.aclose()