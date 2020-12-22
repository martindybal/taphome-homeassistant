from enum import Enum


class ValueType(Enum):
    SensorBrightness = 2
    Humidity = 3
    RealTemperature = 5
    DesiredTemperature = 6
    DeviceStatus = 7
    BlindsSlope = 10
    RainCounter = 13
    WindSpeed = 14
    AlarmMode = 19
    AlarmState = 20
    SalarmActiveDeviceCount = 21
    OperationMode = 22
    ManualTimeout = 23
    Co2 = 24
    ButtonHeldState = 38
    HueDegrees = 40
    Saturation = 41
    AnalogOutputValue = 42
    ReedContact = 44
    Smoke = 45
    BlindsLevel = 46
    FloodState = 47
    SwitchState = 48
    MultiValueSwitchState = 49
    ButtonPressed = 52
    AnalogInputValue = 55
    TotalImpulseCount = 56
    CurrentHourImpulseCount = 57
    LastMeasuredFrequency = 58
    ElectricityConsumption = 59
    ElectricityDemand = 60
    VariableState = 62
    DoorbellState = 64
    HueBrightness = 65
    BlindsIsMoving = 66
    AnalogOutputDesiredValue = 67
    HueBrightnessDesiredValue = 68
    MultiValueSwitchDesiredState = 71
    PWMOutputState = 72
