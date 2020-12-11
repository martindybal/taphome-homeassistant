from .Device import Device
from .TapHomeHttpClientFactory import TapHomeHttpClientFactory


class DiscoverService:
    def __init__(self, tapHomeHttpClient: TapHomeHttpClientFactory._TapHomeHttpClient):
        self.tapHomeHttpClient = tapHomeHttpClient

    async def async_discovery_devices(self):
        json = await self.tapHomeHttpClient.async_api_get("discovery")
        devices = list(
            map(lambda device: Device.create(device), json["devices"])
        )

        return devices