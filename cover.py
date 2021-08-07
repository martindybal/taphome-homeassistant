"""TapHome light integration."""
import typing

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DEVICE_CLASS_BLIND,
    DEVICE_CLASS_SHADE,
    DOMAIN,
    SUPPORT_CLOSE,
    SUPPORT_CLOSE_TILT,
    SUPPORT_OPEN,
    SUPPORT_OPEN_TILT,
    SUPPORT_SET_POSITION,
    SUPPORT_SET_TILT_POSITION,
    CoverEntity,
)
from homeassistant.const import CONF_COVERS
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import *
from .taphome_entity import *
from .taphome_sdk import *


class CoverConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)

    @property
    def device_class(self):
        return self._device_class


class TapHomeCover(TapHomeEntity[CoverState], CoverEntity):
    """Representation of an cover"""

    def __init__(
        self,
        core_name: str,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        cover_service: CoverService,
    ):
        super().__init__(core_name, config_entry, DOMAIN, coordinator, CoverState)
        self.cover_service = cover_service
        self._device_class = config_entry.device_class
        self._supported_features = None

    @property
    def device_class(self):
        """Return the class of the device."""
        return self._device_class

    @property
    def supported_features(self):
        """Flag supported features."""
        default = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

        if self._supported_features is None and self.taphome_state is None:
            return default

        if self._supported_features is None:
            self._supported_features = default

            if self.taphome_state.blinds_slope is not None:
                self._supported_features = (
                    self._supported_features
                    | SUPPORT_OPEN_TILT
                    | SUPPORT_CLOSE_TILT
                    | SUPPORT_SET_TILT_POSITION
                )

            if self._device_class is None:
                if self._supported_features & SUPPORT_SET_TILT_POSITION:
                    self._device_class = DEVICE_CLASS_BLIND
                else:
                    self._device_class = DEVICE_CLASS_SHADE

        return self._supported_features

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self.current_cover_position is None:
            return None
        return self.current_cover_position == 0

    @property
    def current_cover_position(self):
        if (
            not self.taphome_state is None
            and self.taphome_state.blinds_level is not None
        ):
            return self.convert_taphome_percentage_to_ha(
                1 - self.taphome_state.blinds_level
            )

    @property
    def current_cover_tilt_position(self):
        if (
            not self.taphome_state is None
            and self.taphome_state.blinds_slope is not None
        ):
            return self.convert_taphome_percentage_to_ha(
                1 - self.taphome_state.blinds_slope
            )

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self.async_set_cover_position(position=0)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            ha_position = kwargs.get(ATTR_POSITION)
            taphome_position = 1 - self.convert_ha_percentage_to_taphome(ha_position)

            async with UpdateTapHomeState(self) as state:
                await self.cover_service.async_set_level(
                    self.taphome_device, taphome_position
                )
                state.blinds_level = taphome_position

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        await self.async_set_cover_tilt_position(tilt_position=100)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        await self.async_set_cover_tilt_position(tilt_position=0)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover to a specific position."""
        if ATTR_TILT_POSITION in kwargs:
            ha_tilt = kwargs.get(ATTR_TILT_POSITION)
            taphome_tilt = 1 - self.convert_ha_percentage_to_taphome(ha_tilt)

            async with UpdateTapHomeState(self) as state:
                await self.cover_service.async_set_slope(
                    self.taphome_device, taphome_tilt
                )
                state.blinds_slope = taphome_tilt


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the cover platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_COVERS
    ]
    covers = []
    for add_entry_request in add_entry_requests:
        cover_service = CoverService(add_entry_request.tapHome_api_service)
        cover = TapHomeCover(
            add_entry_request.core_name,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            cover_service,
        )
        covers.append(cover)

    add_entities(covers)
