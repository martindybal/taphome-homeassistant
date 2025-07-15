"""Factory for creating lightweight TapHome HTTP clients."""

import logging

import aiohttp
from aiohttp.client_reqrep import ClientResponse, ClientResponseError

_LOGGER = logging.getLogger(__name__)


class TapHomeHttpClientFactory:
    """Create HTTP client instances for communication with TapHome."""

    class _TapHomeHttpClient:
        """Internal HTTP client wrapper used by the SDK."""

        def __init__(self, api_url: str, token: str):
            """Initialize the client with ``api_url`` and ``token``."""
            self.api_url = api_url
            self.token = token

        async def async_api_get(self, endpoint: str):
            """Perform GET request on ``endpoint`` and return JSON response."""
            async with aiohttp.ClientSession() as session:
                request_url = self.__get_request_url(endpoint)
                _LOGGER.debug("TapHome get %s", request_url)
                headers = self.__get_authorization_header()
                async with session.get(request_url, headers=headers) as response:
                    return await self.__get_json(response)

        async def async_api_post(self, endpoint: str, body):
            """Perform POST request on ``endpoint`` with ``body``."""
            async with aiohttp.ClientSession() as session:
                request_url = self.__get_request_url(endpoint)
                _LOGGER.debug("TapHome post %s", request_url)
                headers = self.__get_authorization_header()
                async with session.post(
                    request_url, headers=headers, json=body
                ) as response:
                    return await self.__get_json(response)

        async def __get_json(self, response: ClientResponse):
            """Return JSON payload or raise for non-success response."""
            try:
                if response.status == 200:
                    return await response.json()
                raise ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=response.reason,
                    headers=response.headers,
                )
            except:
                _LOGGER.debug(
                    "Request %s %s\nstatus %s %s\nheaders %s\ntext %s\n",
                    response.url,
                    response.request_info.headers,
                    response.status,
                    response.reason,
                    response.headers,
                    await response.text(),
                )
                raise

        def __get_request_url(self, endpoint: str):
            """Construct request URL for ``endpoint``."""
            return f"{self.api_url}/{endpoint}"

        def __get_authorization_header(self):
            """Return authorization header for HTTP requests."""
            return {"Authorization": f"TapHome {self.token}"}

    def create(self, api_url: str, token: str):
        """Return a new HTTP client for ``api_url`` and ``token``."""
        return TapHomeHttpClientFactory._TapHomeHttpClient(api_url, token)
