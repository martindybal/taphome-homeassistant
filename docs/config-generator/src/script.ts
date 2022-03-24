declare var Vue: any;

enum HomeAssistantEntityType {
    binarySensor = "binary sensor",
    button = "button",
    climate = "climate",
    cover = "cover",
    light = "light",
    sensor = "sensor",
    switch = "switch",
    multivalueSwitches = "multivalue switch",
};

enum TapHomeValueType {
    sensorBrightness = 2,
    humidity = 3,
    realTemperature = 5,
    desiredTemperature = 6,
    deviceStatus = 7,
    blindsSlope = 10,
    raining = 12,
    rainCounter = 13,
    windSpeed = 14,
    alarmMode = 19,
    alarmState = 20,
    alarmActiveDeviceCount = 21,
    operationMode = 22,
    manualTimeout = 23,
    co2 = 24,
    minTemperature = 33,
    maxTemperature = 34,
    pressure = 25,
    noise = 26,
    snowCounter = 28,
    buttonHeldState = 38,
    hueDegrees = 40,
    saturation = 41,
    analogOutputValue = 42,
    reedContact = 44,
    smoke = 45,
    blindsLevel = 46,
    floodState = 47,
    switchState = 48,
    multiValueSwitchState = 49,
    motion = 51,
    buttonPressed = 52,
    voc = 54,
    analogInputValue = 55,
    totalImpulseCount = 56,
    currentHourImpulseCount = 57,
    lastMeasuredFrequency = 58,
    electricityConsumption = 59,
    electricityDemand = 60,
    totalElectricityConsumption = 61,
    variableState = 62,
    doorbellState = 64,
    hueBrightness = 65,
    blindsIsMoving = 66,
    analogOutputDesiredValue = 67,
    hueBrightnessDesiredValue = 68,
    accessControlResult = 70,
    multiValueSwitchDesiredState = 71,
    pwmOutputState = 72,
    batteryPercentageRemaining = 73,
};

class TapHomeDevice {
    deviceId: number;
    name: string;
    description: string;
    supportedValues: [];
    possibleEntityTypes: HomeAssistantEntityType[];
    entityType: HomeAssistantEntityType;
    isSelected: boolean;

    deviceClass: string;

    defaultButtonAction: string;
    buttonAction: string;

    climateMinTemperature: number;
    climateMaxTemperature: number;
    climateHeatingSwitchIdingCoolingModeId: number;
    climateHeatingSwitchId: number;
    climateCoolingSwitchId: number;

    constructor() {
        this.deviceId = undefined;
        this.name = "";
        this.description = "";
        this.supportedValues = [];
        this.possibleEntityTypes = [];
        this.entityType = undefined;
        this.isSelected = true;

        this.defaultButtonAction = "Press";
        this.buttonAction = this.defaultButtonAction;
    }

    get config() {
        if (!this.isSelected) {
            return "";
        } else if (this.entityType === HomeAssistantEntityType.switch || this.entityType === HomeAssistantEntityType.cover) {
            return this.deviceClassConfig;
        } else if (this.entityType === HomeAssistantEntityType.climate) {
            return this.climateConfig;
        } else if (this.entityType === HomeAssistantEntityType.button) {
            return this.buttonConfig;
        }
        return this.idConfig;
    }

    private get deviceClassConfig() {
        if (this.deviceClass) {
            let config = `\n        - id: ${this.deviceId}\n          device_class: ${this.deviceClass}`;
            return config;
        }
        return this.idConfig;
    }

    private get buttonConfig() {
        var hasCustomAction = this.buttonAction && this.buttonAction != this.defaultButtonAction;
        if (hasCustomAction || this.deviceClass) {
            let config = `\n        - id: ${this.deviceId}`;            
            if(hasCustomAction){
                config += `\n          action: ${this.buttonAction}`;
            }
            if(this.deviceClass){
                config += `\n          device_class: ${this.deviceClass}`;
            }
            return config;
        }
        return this.idConfig;
    }


    private get climateConfig() {
        if (this.climateMinTemperature ||
            this.climateMaxTemperature ||
            this.climateHeatingSwitchIdingCoolingModeId ||
            this.climateHeatingSwitchId ||
            this.climateCoolingSwitchId) {
            let config = `\n        - id: ${this.deviceId}`
            if (this.climateMinTemperature) {
                config += `\n          min_temperature: ${this.climateMinTemperature}`;
            } 
            if (this.climateMaxTemperature) {
                config += `\n          max_temperature: ${this.climateMaxTemperature}`;
            } 
            if (this.climateHeatingSwitchIdingCoolingModeId) {
                config += `\n          heating_cooling_mode_id: ${this.climateHeatingSwitchIdingCoolingModeId}`;
            } else if (this.climateHeatingSwitchId) {
                config += `\n          heating_switch_id: ${this.climateHeatingSwitchId}`;
            } else if (this.climateCoolingSwitchId) {
                config += `\n          cooling_switch_id: ${this.climateCoolingSwitchId}`;
            }
            return config;
        }
        return this.idConfig;
    }

    private get idConfig() {
        return `\n        - ${this.deviceId}`;
    }
};

class TapHomeCore {
    id: string;
    token: string;
    apiUrl: string;
    webhookId: string;
    devices: TapHomeDevice[];
    unsupportedDevices: TapHomeDevice[];

    constructor(token, devices) {
        this.token = token;
        this.devices = devices;
        this.unsupportedDevices = [];
    }

    get config() {
        let selectedDevices = this.devices.filter(device => device.isSelected && device.entityType);
        if (selectedDevices.length === 0) {
            return "";
        }
        return `    - ${this.idConfig()}token: ${this.token}${this.apiUrlConfig()}${this.webhookIdConfig()}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.button)}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.light)}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.cover)}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.climate)}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.switch)}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.sensor)}${this.entitiesConfig(selectedDevices, HomeAssistantEntityType.binarySensor)}\n`
    }

    private idConfig() {
        if (!this.id) {
            return "";
        }
        return `id: ${this.id}\n      `;
    }

    private apiUrlConfig() {
        if (!this.apiUrl) {
            return "";
        }
        return `\n      api_url: ${this.apiUrl}`;
    }

    private webhookIdConfig() {
        if (!this.webhookId) {
            return "";
        }
        return `\n      webhook_id: ${this.webhookId}`;
    }

    private entitiesConfig(selectedDevices, entityType) {
        const configSectionName = {};
        configSectionName[HomeAssistantEntityType.light] = "lights";
        configSectionName[HomeAssistantEntityType.cover] = "covers";
        configSectionName[HomeAssistantEntityType.climate] = "climates";
        configSectionName[HomeAssistantEntityType.switch] = "switches";
        configSectionName[HomeAssistantEntityType.multivalueSwitches] = "multivalue_switches";
        configSectionName[HomeAssistantEntityType.sensor] = "sensors";
        configSectionName[HomeAssistantEntityType.binarySensor] = "binary_sensors";
        configSectionName[HomeAssistantEntityType.button] = "buttons";

        let entities = selectedDevices.filter((device) => device.entityType == entityType);
        if (entities.length === 0) {
            return "";
        }
        return `\n      ${configSectionName[entityType]}:${entities.map((device) => device.config).join("")}`;
    }

    loadFromCloudApi = async () => {
        this.devices = [];
        this.unsupportedDevices = [];
        let apiUrl = 'https://cloudapi.taphome.com/api/cloudapi/v1';

        let getAllDevicesValuesUrl = `${apiUrl}/getAllDevicesValues?token=${this.token}`;
        let getAllDevicesValuesResponse = await fetch(getAllDevicesValuesUrl);
        
        if (getAllDevicesValuesResponse.status == 401 || getAllDevicesValuesResponse.status == 403) {
            alert('Core was not found. Please check your token and api_url.');
            return;
        }
        else if (getAllDevicesValuesResponse.status != 200){
            alert('Your core is not supported! Please upgrade your core.');
            return;
        }

        let discoveryUrl = `${apiUrl}/discovery?token=${this.token}`;
        let discoveryResponse = await fetch(discoveryUrl);
        let discoveryJson = await discoveryResponse.json();

        for (const device of discoveryJson.devices) {
            let possibleEntityTypes: HomeAssistantEntityType[] = [];
            let deviceSupportValue = value => device.supportedValues.some(supportedValue => supportedValue.valueTypeId == value);

            if (deviceSupportValue(TapHomeValueType.switchState)) {
                if (deviceSupportValue(TapHomeValueType.analogOutputValue) || deviceSupportValue(TapHomeValueType.hueBrightness)) {
                    possibleEntityTypes.push(HomeAssistantEntityType.light);
                } else if (deviceSupportValue(TapHomeValueType.multiValueSwitchState)) {
                    possibleEntityTypes.push(HomeAssistantEntityType.multivalueSwitches);
                }
                else {
                    possibleEntityTypes.push(HomeAssistantEntityType.light);
                    possibleEntityTypes.push(HomeAssistantEntityType.switch);
                }
            }

            if (deviceSupportValue(TapHomeValueType.blindsLevel)) {
                possibleEntityTypes.push(HomeAssistantEntityType.cover);
            }

            if (deviceSupportValue(TapHomeValueType.desiredTemperature)) {
                possibleEntityTypes.push(HomeAssistantEntityType.climate);
            }

            if ((deviceSupportValue(TapHomeValueType.humidity) && !deviceSupportValue(TapHomeValueType.desiredTemperature)) ||
                (deviceSupportValue(TapHomeValueType.realTemperature) && !deviceSupportValue(TapHomeValueType.desiredTemperature)) ||
                deviceSupportValue(TapHomeValueType.electricityDemand) ||
                deviceSupportValue(TapHomeValueType.electricityConsumption) ||
                deviceSupportValue(TapHomeValueType.co2) ||
                deviceSupportValue(TapHomeValueType.sensorBrightness) ||
                deviceSupportValue(TapHomeValueType.windSpeed) ||
                deviceSupportValue(TapHomeValueType.analogInputValue) ||
                deviceSupportValue(TapHomeValueType.totalImpulseCount) ||
                deviceSupportValue(TapHomeValueType.currentHourImpulseCount) ||
                deviceSupportValue(TapHomeValueType.lastMeasuredFrequency) ||
                deviceSupportValue(TapHomeValueType.variableState)) {
                possibleEntityTypes.push(HomeAssistantEntityType.sensor);
            }

            if (deviceSupportValue(TapHomeValueType.motion) ||
                deviceSupportValue(TapHomeValueType.reedContact) ||
                deviceSupportValue(TapHomeValueType.variableState)) {
                possibleEntityTypes.push(HomeAssistantEntityType.binarySensor);
            }

            if (deviceSupportValue(TapHomeValueType.buttonPressed)) {
                possibleEntityTypes.push(HomeAssistantEntityType.button);
            }

            let entityType = possibleEntityTypes.length == 1 ? possibleEntityTypes[0] : undefined;
            let isSelected: boolean;

            let deviceCollection: TapHomeDevice[];
            if (possibleEntityTypes.length > 0) {
                deviceCollection = this.devices;
                isSelected = true;
            } else {
                deviceCollection = this.unsupportedDevices;
                isSelected = false;
            }

            let taphomeDevice = deviceCollection.find(d => d.deviceId == device.deviceId)
            if (!taphomeDevice) {
                taphomeDevice = new TapHomeDevice();
                deviceCollection.push(taphomeDevice);
            }

            taphomeDevice.deviceId = device.deviceId;
            taphomeDevice.name = device.name;
            taphomeDevice.description = device.description;
            taphomeDevice.supportedValues = device.supportedValues;
            taphomeDevice.possibleEntityTypes = possibleEntityTypes;
            taphomeDevice.entityType = entityType;
            taphomeDevice.isSelected = isSelected;
        }
    };
};

let ViewModel = class {
    taphomeCores: TapHomeCore[];
    HomeAssistantEntityType;
    TapHomeValueType;

    constructor() {
        this.taphomeCores = [];
        this.HomeAssistantEntityType = HomeAssistantEntityType;
        this.TapHomeValueType = TapHomeValueType;
        this.addCore();
    }

    addCore() {
        this.taphomeCores.push(new TapHomeCore("", []));
    }

    loadFromConfig(config) {
        //TODO Read config
        console.log(config);
    }

    get config() {
        let coresConfig = this.taphomeCores.map(core => core.config).join("");
        if (!coresConfig) {
            return "";
        }
        return `taphome:\n  cores:\n${coresConfig}`;
    }
};


var viewModel = new ViewModel();

var app = new Vue({
    el: "#app",
    data: viewModel,
    methods: {
        copyConfig: function () {
            let copyTextarea = <HTMLTextAreaElement>document.getElementById('config-textarea');
            copyTextarea.focus();
            copyTextarea.select();
            document.execCommand('copy')
        },
        addCore: function () {
            viewModel.addCore();
        }
    },
    computed: {
        config: {
            get() {
                return viewModel.config;
            },
            set(yaml) {
                viewModel.loadFromConfig(yaml);
                return viewModel.config;
            },
        },
    },
});
