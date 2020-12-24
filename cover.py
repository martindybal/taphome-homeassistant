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

from . import TAPHOME_API_SERVICE, TAPHOME_DEVICES
from datetime import timedelta

SCAN_INTERVAL = timedelta(seconds=10)
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, platformConfig):
    tapHomeApiService = platformConfig[TAPHOME_API_SERVICE]
    devices = platformConfig[TAPHOME_DEVICES]
    coverService = CoverService(tapHomeApiService)

    covers = []
    for device in devices:
        cover = await async_create_cover(coverService, device)
        covers.append(cover)

    async_add_entities(covers)


# async def async_create_cover(coverService: CoverService, device: Device):
async def async_create_cover(coverService, device: Device):
    cover = TapHomeCover(coverService, device)
    await cover.async_refresh_state()
    return cover


class TapHomeCover(CoverEntity):
    """Representation of an Cover"""

    def __init__(self, coverService: CoverService, device: Device):
        self._coverService = coverService
        self._device = device
        self._state = None
        self._position = None
        self._tilt = None
        self._supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

        if ValueType.BlindsSlope in device.supportedValues:
            self._supported_features = (
                self._supported_features | SUPPORT_SET_TILT_POSITION
            )

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def name(self):
        """Return the name of the cover."""
        return self._device.name

    @property
    def current_cover_position(self):
        return self._position

    @property
    def current_cover_tilt_position(self):
        return self._tilt

    @property
    def device_class(self):
        """Return the class of the device."""
        if self._supported_features & SUPPORT_SET_TILT_POSITION:
            return DEVICE_CLASS_BLIND
        else:
            return DEVICE_CLASS_SHADE

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self._position is None:
            return None
        return self._position == 0

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self.__async_set_cover_position(100)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self.__async_set_cover_position(0)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs.get(ATTR_POSITION)
            await self.__async_set_cover_position(position)

    async def __async_set_cover_position(self, position):
        taphomePosition = 1 - position / 100
        result = await self._coverService.async_set_cover_position(
            self._device, taphomePosition
        )

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._position = position

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover til to a specific position."""
        tilt = kwargs.get(ATTR_TILT_POSITION)
        taphomeTilt = 1 - tilt / 100
        result = await self._coverService.async_set_cover_tilt(
            self._device, taphomeTilt
        )

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._tilt = tilt

    def async_update(self, **kwargs):
        """Update cover."""
        return self.async_refresh_state()

    async def async_refresh_state(self):
        state = await self._coverService.async_get_cover_state(self._device)
        if state.blinds_level is None:
            self._position = None
        else:
            self._position = 100 - state.blinds_level * 100

        if state.blinds_slope is None:
            self._tilt = None
        else:
            self._tilt = 100 - state.blinds_slope * 100