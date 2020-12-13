"""TapHome cover integration."""
from voluptuous.schema_builder import Self
from .taphome_sdk import *

import logging
from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    DEVICE_CLASS_BLIND,
    DEVICE_CLASS_SHADE,
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_SET_POSITION,
    SUPPORT_SET_TILT_POSITION,
)

from . import TAPHOME_API_SERVICE

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, devices: list):
    tapHomeApiService = hass.data[TAPHOME_API_SERVICE]
    coverService = CoverService(tapHomeApiService)

    covers = []
    for device in devices:
        cover = await async_create_cover(coverService, device)
        covers.append(cover)

    async_add_entities(covers)


# async def async_create_cover(coverService: CoverService, device: Device):
async def async_create_cover(coverService, device: Device):
    cover = TapHomeCover(
        coverService, device.deviceId, device.name, device.supportedValues
    )
    await cover.async_refresh_state()
    return cover


class TapHomeCover(CoverEntity):
    """Representation of an Cover"""

    def __init__(
        self, coverService: CoverService, deviceId: int, name: str, supportedValues
    ):
        self._coverService = coverService
        self._name = name
        self._deviceId = deviceId
        self._state = None
        self._supported_features = (
            SUPPORT_OPEN
            | SUPPORT_CLOSE
            | SUPPORT_SET_POSITION
            | SUPPORT_SET_TILT_POSITION
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def device_class(self):
        """Return the class of the device."""
        return DEVICE_CLASS_BLIND

    @property
    def is_closed(self):
        """Return if the blind is closed or not."""
        if self._state[ValueType.BlindsLevel] == 1:
            return True
        return None

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        print(f"Open cover {self.name}")
        print(kwargs)
        await self.__async_set_cover_position(0)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self.__async_set_cover_position(100)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs.get(ATTR_POSITION)
            await self.__async_set_cover_position(position)

    async def __async_set_cover_position(self, position):
        taphomePosition = position / 100
        await self._coverService.async_set_cover_position(
            self._deviceId, taphomePosition
        )

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover til to a specific position."""
        tilt = kwargs.get(ATTR_TILT_POSITION)
        taphomeTilt = tilt / 100
        await self._coverService.async_set_cover_tilt(self._deviceId, taphomeTilt)

    def async_update(self, **kwargs):
        """Update cover."""
        return self.async_refresh_state()

    async def async_refresh_state(self):
        self._state = await self._coverService.async_get_cover_state(self._deviceId)