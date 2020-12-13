from enum import Enum


class ValueType(Enum):
    SensorBrightness = 2    
    Humidity = 3
    RealTemperature = 5
    DesiredTemperature = 6
    DeviceStatus = 7
    BlindsSlope = 10
    WindSpeed = 14
    AlarmMode = 19
    AlarmState = 20
    Co2 = 24
    SalarmActiveDeviceCount = 21
    ButtonHeldState = 38
    HueDegrees = 40
    Saturation = 41
    AnalogOutputValue = 42
    ReedContact = 44
    BlindsLevel = 46
    SwitchState = 48
    MultiValueSwitchState = 49
    ButtonPressed = 52
    ElectricityConsumption = 59
    ElectricityDemand = 60
    VariableState = 62
    DoorbellState = 64
    HueBrightness = 65
    BlindsIsMoving = 66
    AnalogOutputDesiredValue = 67
    HueBrightnessDesiredValue = 68
    MultiValueSwitchDesiredState = 71
