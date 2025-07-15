"""TapHome cover integration."""

import copy

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import CONF_COVERS
from homeassistant.core import HomeAssistant, callback

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import UpdateTapHomeState
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinator,
    TapHomeEntity,
)
from .taphome_sdk import CoverService, CoverState


class CoverConfigEntry(TapHomeConfigEntry):
    """Configuration options specific to TapHome covers."""

    def __init__(self, device_config: dict) -> None:
        """Initialize cover config entry."""
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)
        self._close_threshold = self.get_optional("close_threshold", 100)

    @property
    def device_class(self):
        """Return Home Assistant cover device class if configured."""
        return self._device_class

    @property
    def close_threshold(self):
        """Return threshold determining closed state."""
        return self._close_threshold


class TapHomeCover(TapHomeEntity[CoverState], CoverEntity):
    """Representation of an cover."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: CoverConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        cover_service: CoverService,
    ) -> None:
        """Initialize TapHome cover entity."""
        super().__init__(
            hass,
            core_config,
            config_entry,
            COVER_DOMAIN,
            coordinator,
            CoverState,
        )
        self.cover_service = cover_service
        self._device_class = config_entry.device_class
        self._close_threshold = config_entry.close_threshold
        self._supported_features = None
        self._is_opening = False
        self._is_closing = False

    @property
    def device_class(self):
        """Return the class of the device."""
        return self._device_class

    @property
    def supported_features(self):
        """Flag supported features."""
        default = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )

        if self._supported_features is None and self.taphome_state is None:
            return default

        if self._supported_features is None:
            self._supported_features = default

            if self.taphome_state.blinds_slope is not None:
                self._supported_features = (
                    self._supported_features
                    | CoverEntityFeature.OPEN_TILT
                    | CoverEntityFeature.CLOSE_TILT
                    | CoverEntityFeature.SET_TILT_POSITION
                )

            if self._device_class is None:
                if self._supported_features & CoverEntityFeature.SET_TILT_POSITION:
                    self._device_class = CoverDeviceClass.BLIND
                else:
                    self._device_class = CoverDeviceClass.SHADE

        return self._supported_features

    @property
    def current_cover_position(self):
        """Return current cover position as a percentage."""
        if (
            self.taphome_state is not None
            and self.taphome_state.blinds_level is not None
        ):
            return self.convert_taphome_percentage_to_ha(
                1 - self.taphome_state.blinds_level
            )
        return None

    @property
    def current_cover_tilt_position(self):
        """Return current tilt position as a percentage."""
        if (
            self.taphome_state is not None
            and self.taphome_state.blinds_slope is not None
        ):
            return self.convert_taphome_percentage_to_ha(
                1 - self.taphome_state.blinds_slope
            )
        return None

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self.taphome_state.blinds_level is None:
            return None
        return self.taphome_state.blinds_level >= self._close_threshold / 100

    @property
    def is_opening(self) -> bool:
        """Return ``True`` while the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return ``True`` while the cover is closing."""
        return self._is_closing

    @callback
    def handle_taphome_state_change(self, last_state: CoverState) -> None:
        """Handle updates of TapHome cover state."""
        self.handle_moving(self.taphome_state, last_state)
        super().handle_taphome_state_change(last_state)

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

            # TapHome also adjusts the tilt of the blind when changing the position. This is not a demanding behavior for me. So I use the existing tilt to preserve the value
            taphome_tilt = None
            if self.current_cover_tilt_position is not None:
                if taphome_position == 0:
                    taphome_tilt = 0
                else:
                    taphome_tilt = 1 - self.convert_ha_percentage_to_taphome(
                        self.current_cover_tilt_position
                    )

            async with UpdateTapHomeState(self) as state:
                last_state = copy.deepcopy(state)
                await self.cover_service.async_set_level(
                    self.taphome_device, taphome_position, taphome_tilt
                )
                state.blinds_is_moving = True
                state.blinds_level = taphome_position
                self.handle_moving(state, last_state)

    def handle_moving(self, current_state: CoverState, last_state: CoverState) -> None:
        """Update internal moving flags according to state change."""
        if (
            current_state is not None
            and last_state is not None
            and current_state.blinds_is_moving
        ):
            if current_state.blinds_level > last_state.blinds_level:
                self._is_closing = True
                self._is_opening = False
            elif current_state.blinds_level < last_state.blinds_level:
                self._is_opening = True
                self._is_closing = False
        else:
            self._is_opening = False
            self._is_closing = False

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
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][CONF_COVERS]
    covers = []
    for add_entry_request in add_entry_requests:
        cover_service = CoverService(add_entry_request.taphome_api_service)
        cover = TapHomeCover(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            cover_service,
        )
        covers.append(cover)

    add_entities(covers)
