import aiohttp

class TapHomeHttpClientFactory:
    class _TapHomeHttpClient:
        def __init__(self, token: str):
            self.apiUrl = "https://cloudapi.taphome.com/api/CloudApi/v1"
            self.token = token

        async def async_api_get(self, endpoint: str):
            async with aiohttp.ClientSession() as session:
                requestUrl = self.__get_request_url(endpoint)
                headers = self.__get_authorization_header()
                async with session.get(requestUrl, headers=headers) as response:
                    return await response.json()

        async def async_api_post(self, endpoint: str, body):
            async with aiohttp.ClientSession() as session:
                requestUrl = self.__get_request_url(endpoint)
                headers = self.__get_authorization_header()
                async with session.post(
                    requestUrl, headers=headers, json=body
                ) as response:
                    return await response.json()

        def __get_request_url(self, endpoint: str):
            return f"{self.apiUrl}/{endpoint}"

        def __get_authorization_header(self):
            return {"Authorization": f"TapHome {self.token}"}

    def create(self, token: str):
        return TapHomeHttpClientFactory._TapHomeHttpClient(token)