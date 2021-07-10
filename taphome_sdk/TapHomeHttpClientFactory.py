import logging

import aiohttp
from aiohttp.client_reqrep import ClientResponse, ClientResponseError

_LOGGER = logging.getLogger(__name__)


class TapHomeHttpClientFactory:
    class _TapHomeHttpClient:
        def __init__(self, api_url: str, token: str):
            self.api_url = api_url
            self.token = token

        async def async_api_get(self, endpoint: str):
            async with aiohttp.ClientSession() as session:
                requestUrl = self.__get_request_url(endpoint)
                _LOGGER.info(f"TapHome get {requestUrl}")
                headers = self.__get_authorization_header()
                async with session.get(requestUrl, headers=headers) as response:
                    return await self.__get_json(response)

        async def async_api_post(self, endpoint: str, body):
            async with aiohttp.ClientSession() as session:
                requestUrl = self.__get_request_url(endpoint)
                _LOGGER.info(f"TapHome post {requestUrl}")
                headers = self.__get_authorization_header()
                async with session.post(
                    requestUrl, headers=headers, json=body
                ) as response:
                    return await self.__get_json(response)

        async def __get_json(self, response: ClientResponse):
            try:
                if response.status == 200:
                    return await response.json()
                else:
                    raise ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=response.reason,
                        headers=response.headers,
                    )
            except:
                _LOGGER.warning(
                    f"request {response.url} {response.request_info.headers}\nstatus {response.status} {response.reason}\nheaders {response.headers}\ntext {await response.text()}\n"
                )
                raise

        def __get_request_url(self, endpoint: str):
            return f"{self.api_url}/{endpoint}"

        def __get_authorization_header(self):
            return {"Authorization": f"TapHome {self.token}"}

    def create(self, api_url: str, token: str):
        return TapHomeHttpClientFactory._TapHomeHttpClient(api_url, token)
