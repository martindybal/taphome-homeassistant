"""TapHome time integration."""

from datetime import time
from functools import cached_property
import logging
import typing

from homeassistant.components.time import DOMAIN as TIME_DOMAIN, TimeEntity
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_TIMES, TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator, UpdateTapHomeState
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry, TapHomeEntity
from .taphome_sdk.time_service import TimeService, TimeState

_LOGGER = logging.getLogger(__name__)


class TapHomeTime(TapHomeEntity[TimeState], TimeEntity):
    """Representation of an time."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        time_service: TimeService,
    ):
        super().__init__(
            hass,
            core_config,
            config_entry,
            TIME_DOMAIN,
            coordinator,
            TimeState,
        )
        self.time_service = time_service

    @property
    def native_value(self) -> time | None:
        """Return the value reported by the time."""
        if self.taphome_state is None:
            return None
        return self.seconds_to_time(self.taphome_state.total_seconds)

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""

        total_seconds = value.hour * 3600 + value.minute * 60 + value.second
        async with UpdateTapHomeState(self) as state:
            await self.time_service.async_set_value(total_seconds, self.taphome_device)
            state.total_seconds = total_seconds

    def seconds_to_time(self, seconds: int) -> time | None:
        one_day_total_seconds = 86400
        if seconds > one_day_total_seconds:
            _LOGGER.error(
                "Seconds value cannot exceed one day (86400 seconds). %s has value %s",
                self.entity_id,
                seconds,
            )
            return None

        # Extract hours, minutes, and seconds from the timedelta object
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return time(hour=hours, minute=minutes, second=seconds)


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the time platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_TIMES
    ]

    times = [
        TapHomeTime(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            TimeService(add_entry_request.taphome_api_service),
        )
        for add_entry_request in add_entry_requests
    ]

    add_entities(times)
