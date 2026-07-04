"""TapHome cover integration."""

from __future__ import annotations

from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry
from .taphome_entity import TapHomeEntity
from .taphome_sdk import BidirectionalDevice, BidirectionalDeviceState, PositionState


class TapHomeCoverConfig(TapHomeEntityConfig):
    """Configuration for a TapHome cover device."""

    def __init__(self, device_config: dict) -> None:
        """Store config and extract cover limits."""
        super().__init__(device_config)
        self.device_class: CoverDeviceClass = self.get_optional("device_class", None)
        self.close_threshold: int | None = self.get_optional("close_threshold", None)


class TapHomeCover(TapHomeEntity, CoverEntity):
    """Representation of a cover."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeCoverConfig],
    ) -> None:
        """Initialize TapHome cover entity."""

        self._cover = config.hub.get_typed_device(config.entity.id, BidirectionalDevice)

        self._attr_device_class = config.entity.device_class
        self._taphome_close_threshold = self.invert_ha_percentage_to_th(
            config.entity.close_threshold
        )

        self._attr_supported_features = (
            CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
        )
        if self._cover.supports_tilt:
            self._attr_supported_features |= (
                CoverEntityFeature.SET_TILT_POSITION
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
            )

        self._cover.state.changed += self._on_cover_state_change
        super().__init__(config, self._cover, COVER_DOMAIN)

    def _on_cover_state_change(
        self,
        _: BidirectionalDeviceState | None,
        current_state: BidirectionalDeviceState,
    ) -> None:
        """Handle cover state change event."""
        self._attr_current_cover_position = self.invert_th_percentage_to_ha(
            current_state.position
        )

        self._attr_current_cover_tilt_position = self.invert_th_percentage_to_ha(
            current_state.tilt
        )

        position_state = current_state.get_inverted_position_state(
            self._taphome_close_threshold
        )
        if position_state is None:
            self._attr_is_opening = None
            self._attr_is_closing = None
            self._attr_is_closed = None
        else:
            self._attr_is_opening = position_state is PositionState.OPENING
            self._attr_is_closing = position_state is PositionState.CLOSING
            self._attr_is_closed = position_state is PositionState.CLOSED

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self.async_set_cover_position(position=0)

    async def async_set_cover_position(self, *, position: int, **kwargs):
        """Move the cover to a specific position."""

        taphome_position = self.invert_ha_percentage_to_th(position)
        # TapHome also adjusts the tilt of the blind when changing the
        # position. This is not a demanding behavior for me, so we reuse
        # the existing tilt to preserve the value
        taphome_tilt = (
            0
            if taphome_position == 0
            else self.invert_ha_percentage_to_th(self.current_cover_tilt_position)
        )
        if taphome_position is not None:
            await self._cover.async_set_position(taphome_position, taphome_tilt)

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        await self.async_set_cover_tilt_position(tilt_position=100)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        await self.async_set_cover_tilt_position(tilt_position=0)

    async def async_set_cover_tilt_position(
        self, *, tilt_position: int | None, **kwargs
    ):
        """Move the cover tilt to a specific position."""

        taphome_tilt = self.invert_ha_percentage_to_th(tilt_position)
        if taphome_tilt is not None:
            await self._cover.async_set_tilt(taphome_tilt)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome covers from a config entry."""
    add_taphome_entities(entry, async_add_entities, COVER_DOMAIN, TapHomeCover)
