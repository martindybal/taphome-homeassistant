from .ValueType import ValueType


class __DeviceServiceHelper:
    def get_device_value(deviceValues: dict, vylueType: ValueType):
        try:
            return next(
                deviceValue
                for deviceValue in deviceValues
                if deviceValue["valueTypeId"] == vylueType.value
            )["value"]
        except:
            return None