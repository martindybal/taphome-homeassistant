import logging
from .Device import Device
from .taphome_device_state import TapHomeState
from .TapHomeApiService import TapHomeApiService
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType

_LOGGER = logging.getLogger(__name__)


class ThermostatState(TapHomeState):
    def __init__(
        self,
        thermostat_values: dict,
    ):
        super().__init__(thermostat_values)

        self.desired_temperature = self.get_device_value(
            thermostat_values, ValueType.DesiredTemperature
        )
        self.real_temperature = self.get_device_value(
            thermostat_values, ValueType.RealTemperature
        )
        self.min_temperature = self.get_device_value(
            thermostat_values, ValueType.MinTemperature
        )
        self.max_temperature = self.get_device_value(
            thermostat_values, ValueType.MaxTemperature
        )

    def __eq__(self, other):
        if isinstance(other, ThermostatState):
            return (
                super().__eq__(other)
                and self.desired_temperature == other.desired_temperature
                and self.real_temperature == other.real_temperature
                and self.min_temperature == other.min_temperature
                and self.max_temperature == other.max_temperature
            )

        return False


class ThermostatService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> ThermostatState:
        try:
            thermostat_values = await self.taphome_api_service.async_get_device_values(
                device.deviceId
            )

            return ThermostatState(thermostat_values)
        except:
            _LOGGER.error(f"TapHome async_get_state for {device.id} failed")
            return None

    def async_set_desired_temperature(
        self, device: Device, desired_temperature
    ) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.DesiredTemperature, desired_temperature
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
