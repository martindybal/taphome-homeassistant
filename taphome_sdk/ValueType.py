from enum import Enum


class ValueType(Enum):
    SensorBrightness = 2    
    Humidity = 3
    RealTemperature = 5
    DesiredTemperature = 6
    DeviceStatus = 7
    BlindsSlope = 10
    ButtonHeldState = 38
    HueDegrees = 40
    Saturation = 41
    AnalogOutputValue = 42
    BlindsLevel = 46
    SwitchState = 48
    MultiValueSwitchState = 49
    ButtonPressed = 52
    AnalogOutputDesiredValue = 67
    MultiValueSwitchDesiredState = 71
    HueBrightness = 65
    BlindsIsMoving = 66
    HueBrightnessDesiredValue = 68
