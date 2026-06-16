import httpx

_client: httpx.AsyncClient | None = None


async def open_client() -> None:
    global _client
    _client = httpx.AsyncClient()


async def close_client() -> None:
    global _client
    if _client:
        await _client.aclose()
    _client = None


def get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialised — was open_client() called?")
    return _client
