var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (_) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var HomeAssistantEntityType;
(function (HomeAssistantEntityType) {
    HomeAssistantEntityType["binarySensor"] = "binary sensor";
    HomeAssistantEntityType["climate"] = "climate";
    HomeAssistantEntityType["cover"] = "cover";
    HomeAssistantEntityType["light"] = "light";
    HomeAssistantEntityType["sensor"] = "sensor";
    HomeAssistantEntityType["switch"] = "switch";
    HomeAssistantEntityType["multivalueSwitches"] = "multivalue switch";
})(HomeAssistantEntityType || (HomeAssistantEntityType = {}));
;
var TapHomeValueType;
(function (TapHomeValueType) {
    TapHomeValueType[TapHomeValueType["sensorBrightness"] = 2] = "sensorBrightness";
    TapHomeValueType[TapHomeValueType["humidity"] = 3] = "humidity";
    TapHomeValueType[TapHomeValueType["realTemperature"] = 5] = "realTemperature";
    TapHomeValueType[TapHomeValueType["desiredTemperature"] = 6] = "desiredTemperature";
    TapHomeValueType[TapHomeValueType["deviceStatus"] = 7] = "deviceStatus";
    TapHomeValueType[TapHomeValueType["blindsSlope"] = 10] = "blindsSlope";
    TapHomeValueType[TapHomeValueType["raining"] = 12] = "raining";
    TapHomeValueType[TapHomeValueType["rainCounter"] = 13] = "rainCounter";
    TapHomeValueType[TapHomeValueType["windSpeed"] = 14] = "windSpeed";
    TapHomeValueType[TapHomeValueType["alarmMode"] = 19] = "alarmMode";
    TapHomeValueType[TapHomeValueType["alarmState"] = 20] = "alarmState";
    TapHomeValueType[TapHomeValueType["alarmActiveDeviceCount"] = 21] = "alarmActiveDeviceCount";
    TapHomeValueType[TapHomeValueType["operationMode"] = 22] = "operationMode";
    TapHomeValueType[TapHomeValueType["manualTimeout"] = 23] = "manualTimeout";
    TapHomeValueType[TapHomeValueType["co2"] = 24] = "co2";
    TapHomeValueType[TapHomeValueType["minTemperature"] = 33] = "minTemperature";
    TapHomeValueType[TapHomeValueType["maxTemperature"] = 34] = "maxTemperature";
    TapHomeValueType[TapHomeValueType["pressure"] = 25] = "pressure";
    TapHomeValueType[TapHomeValueType["noise"] = 26] = "noise";
    TapHomeValueType[TapHomeValueType["snowCounter"] = 28] = "snowCounter";
    TapHomeValueType[TapHomeValueType["buttonHeldState"] = 38] = "buttonHeldState";
    TapHomeValueType[TapHomeValueType["hueDegrees"] = 40] = "hueDegrees";
    TapHomeValueType[TapHomeValueType["saturation"] = 41] = "saturation";
    TapHomeValueType[TapHomeValueType["analogOutputValue"] = 42] = "analogOutputValue";
    TapHomeValueType[TapHomeValueType["reedContact"] = 44] = "reedContact";
    TapHomeValueType[TapHomeValueType["smoke"] = 45] = "smoke";
    TapHomeValueType[TapHomeValueType["blindsLevel"] = 46] = "blindsLevel";
    TapHomeValueType[TapHomeValueType["floodState"] = 47] = "floodState";
    TapHomeValueType[TapHomeValueType["switchState"] = 48] = "switchState";
    TapHomeValueType[TapHomeValueType["multiValueSwitchState"] = 49] = "multiValueSwitchState";
    TapHomeValueType[TapHomeValueType["motion"] = 51] = "motion";
    TapHomeValueType[TapHomeValueType["buttonPressed"] = 52] = "buttonPressed";
    TapHomeValueType[TapHomeValueType["voc"] = 54] = "voc";
    TapHomeValueType[TapHomeValueType["analogInputValue"] = 55] = "analogInputValue";
    TapHomeValueType[TapHomeValueType["totalImpulseCount"] = 56] = "totalImpulseCount";
    TapHomeValueType[TapHomeValueType["currentHourImpulseCount"] = 57] = "currentHourImpulseCount";
    TapHomeValueType[TapHomeValueType["lastMeasuredFrequency"] = 58] = "lastMeasuredFrequency";
    TapHomeValueType[TapHomeValueType["electricityConsumption"] = 59] = "electricityConsumption";
    TapHomeValueType[TapHomeValueType["electricityDemand"] = 60] = "electricityDemand";
    TapHomeValueType[TapHomeValueType["totalElectricityConsumption"] = 61] = "totalElectricityConsumption";
    TapHomeValueType[TapHomeValueType["variableState"] = 62] = "variableState";
    TapHomeValueType[TapHomeValueType["doorbellState"] = 64] = "doorbellState";
    TapHomeValueType[TapHomeValueType["hueBrightness"] = 65] = "hueBrightness";
    TapHomeValueType[TapHomeValueType["blindsIsMoving"] = 66] = "blindsIsMoving";
    TapHomeValueType[TapHomeValueType["analogOutputDesiredValue"] = 67] = "analogOutputDesiredValue";
    TapHomeValueType[TapHomeValueType["hueBrightnessDesiredValue"] = 68] = "hueBrightnessDesiredValue";
    TapHomeValueType[TapHomeValueType["accessControlResult"] = 70] = "accessControlResult";
    TapHomeValueType[TapHomeValueType["multiValueSwitchDesiredState"] = 71] = "multiValueSwitchDesiredState";
    TapHomeValueType[TapHomeValueType["pwmOutputState"] = 72] = "pwmOutputState";
    TapHomeValueType[TapHomeValueType["batteryPercentageRemaining"] = 73] = "batteryPercentageRemaining";
})(TapHomeValueType || (TapHomeValueType = {}));
;
var TapHomeDevice = /** @class */ (function () {
    function TapHomeDevice() {
        this.deviceId = undefined;
        this.name = "";
        this.description = "";
        this.supportedValues = [];
        this.possibleEntityTypes = [];
        this.entityType = undefined;
        this.isSelected = true;
    }
    Object.defineProperty(TapHomeDevice.prototype, "config", {
        get: function () {
            if (!this.isSelected) {
                return "";
            }
            else if (this.entityType === HomeAssistantEntityType.switch || this.entityType === HomeAssistantEntityType.cover) {
                return this.deviceClassConfig;
            }
            else if (this.entityType === HomeAssistantEntityType.climate) {
                return this.climateConfig;
            }
            return this.idConfig;
        },
        enumerable: false,
        configurable: true
    });
    Object.defineProperty(TapHomeDevice.prototype, "deviceClassConfig", {
        get: function () {
            if (this.deviceClass) {
                var config = "\n        - id: " + this.deviceId + "\n          device_class: " + this.deviceClass;
                return config;
            }
            return this.idConfig;
        },
        enumerable: false,
        configurable: true
    });
    Object.defineProperty(TapHomeDevice.prototype, "climateConfig", {
        get: function () {
            if (this.climateMinTemperature ||
                this.climateMaxTemperature ||
                this.climateHeatingSwitchIdingCoolingModeId ||
                this.climateHeatingSwitchId ||
                this.climateCoolingSwitchId) {
                var config = "\n        - id: " + this.deviceId;
                if (this.climateMinTemperature) {
                    config += "\n          min_temperature: " + this.climateMinTemperature;
                }
                if (this.climateMaxTemperature) {
                    config += "\n          max_temperature: " + this.climateMaxTemperature;
                }
                if (this.climateHeatingSwitchIdingCoolingModeId) {
                    config += "\n          heating_cooling_mode_id: " + this.climateHeatingSwitchIdingCoolingModeId;
                }
                else if (this.climateHeatingSwitchId) {
                    config += "\n          heating_switch_id: " + this.climateHeatingSwitchId;
                }
                else if (this.climateCoolingSwitchId) {
                    config += "\n          cooling_switch_id: " + this.climateCoolingSwitchId;
                }
                return config;
            }
            return this.idConfig;
        },
        enumerable: false,
        configurable: true
    });
    Object.defineProperty(TapHomeDevice.prototype, "idConfig", {
        get: function () {
            return "\n        - " + this.deviceId;
        },
        enumerable: false,
        configurable: true
    });
    return TapHomeDevice;
}());
;
var TapHomeCore = /** @class */ (function () {
    function TapHomeCore(token, devices) {
        var _this = this;
        this.loadFromCloudApi = function () { return __awaiter(_this, void 0, void 0, function () {
            var apiUrl, getAllDevicesValuesUrl, getAllDevicesValuesResponse, discoveryUrl, discoveryResponse, discoveryJson, _loop_1, this_1, _i, _a, device;
            var _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        this.devices = [];
                        this.unsupportedDevices = [];
                        apiUrl = (_b = this.apiUrl) !== null && _b !== void 0 ? _b : 'https://cloudapi.taphome.com/api/cloudapi/v1';
                        getAllDevicesValuesUrl = apiUrl + "/getAllDevicesValues/?token=" + this.token;
                        return [4 /*yield*/, fetch(getAllDevicesValuesUrl)];
                    case 1:
                        getAllDevicesValuesResponse = _c.sent();
                        if (getAllDevicesValuesResponse.status == 401) {
                            alert('Core was not found. Please check your token and api_url.');
                            return [2 /*return*/];
                        }
                        else if (getAllDevicesValuesResponse.status != 200) {
                            alert('Your core is not supported! Please upgrade your core.');
                            return [2 /*return*/];
                        }
                        discoveryUrl = apiUrl + "/discovery/?token=" + this.token;
                        return [4 /*yield*/, fetch(discoveryUrl)];
                    case 2:
                        discoveryResponse = _c.sent();
                        return [4 /*yield*/, discoveryResponse.json()];
                    case 3:
                        discoveryJson = _c.sent();
                        _loop_1 = function (device) {
                            var possibleEntityTypes = [];
                            var deviceSupportValue = function (value) { return device.supportedValues.some(function (supportedValue) { return supportedValue.valueTypeId == value; }); };
                            if (deviceSupportValue(TapHomeValueType.switchState)) {
                                if (deviceSupportValue(TapHomeValueType.analogOutputValue) || deviceSupportValue(TapHomeValueType.hueBrightness)) {
                                    possibleEntityTypes.push(HomeAssistantEntityType.light);
                                }
                                else if (deviceSupportValue(TapHomeValueType.multiValueSwitchState)) {
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
                            var entityType = possibleEntityTypes.length == 1 ? possibleEntityTypes[0] : undefined;
                            var isSelected = void 0;
                            var deviceCollection = void 0;
                            if (possibleEntityTypes.length > 0) {
                                deviceCollection = this_1.devices;
                                isSelected = true;
                            }
                            else {
                                deviceCollection = this_1.unsupportedDevices;
                                isSelected = false;
                            }
                            var taphomeDevice = deviceCollection.find(function (d) { return d.deviceId == device.deviceId; });
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
                        };
                        this_1 = this;
                        for (_i = 0, _a = discoveryJson.devices; _i < _a.length; _i++) {
                            device = _a[_i];
                            _loop_1(device);
                        }
                        return [2 /*return*/];
                }
            });
        }); };
        this.token = token;
        this.devices = devices;
        this.unsupportedDevices = [];
    }
    Object.defineProperty(TapHomeCore.prototype, "config", {
        get: function () {
            var selectedDevices = this.devices.filter(function (device) { return device.isSelected && device.entityType; });
            if (selectedDevices.length === 0) {
                return "";
            }
            return "    - " + this.idConfig() + "token: " + this.token + this.apiUrlConfig() + this.updateIntervalConfig() + this.entitiesConfig(selectedDevices, HomeAssistantEntityType.light) + this.entitiesConfig(selectedDevices, HomeAssistantEntityType.cover) + this.entitiesConfig(selectedDevices, HomeAssistantEntityType.climate) + this.entitiesConfig(selectedDevices, HomeAssistantEntityType.switch) + this.entitiesConfig(selectedDevices, HomeAssistantEntityType.sensor) + this.entitiesConfig(selectedDevices, HomeAssistantEntityType.binarySensor) + "\n";
        },
        enumerable: false,
        configurable: true
    });
    TapHomeCore.prototype.idConfig = function () {
        if (!this.id) {
            return "";
        }
        return "id: " + this.id + "\n      ";
    };
    TapHomeCore.prototype.apiUrlConfig = function () {
        if (!this.apiUrl) {
            return "";
        }
        return "\n      api_url: " + this.apiUrl;
    };
    TapHomeCore.prototype.updateIntervalConfig = function () {
        if (!this.updateInterval) {
            return "";
        }
        return "\n      update_interval: " + this.updateInterval;
    };
    TapHomeCore.prototype.entitiesConfig = function (selectedDevices, entityType) {
        var configSectionName = {};
        configSectionName[HomeAssistantEntityType.light] = "lights";
        configSectionName[HomeAssistantEntityType.cover] = "covers";
        configSectionName[HomeAssistantEntityType.climate] = "climates";
        configSectionName[HomeAssistantEntityType.switch] = "switches";
        configSectionName[HomeAssistantEntityType.multivalueSwitches] = "multivalue_switches";
        configSectionName[HomeAssistantEntityType.sensor] = "sensors";
        configSectionName[HomeAssistantEntityType.binarySensor] = "binary_sensors";
        var entities = selectedDevices.filter(function (device) { return device.entityType == entityType; });
        if (entities.length === 0) {
            return "";
        }
        return "\n      " + configSectionName[entityType] + ":" + entities.map(function (device) { return device.config; }).join("");
    };
    return TapHomeCore;
}());
;
var ViewModel = /** @class */ (function () {
    function class_1() {
        this.taphomeCores = [];
        this.HomeAssistantEntityType = HomeAssistantEntityType;
        this.TapHomeValueType = TapHomeValueType;
        this.addCore();
    }
    class_1.prototype.addCore = function () {
        this.taphomeCores.push(new TapHomeCore("", []));
    };
    class_1.prototype.loadFromConfig = function (config) {
        //TODO Read config
        console.log(config);
    };
    Object.defineProperty(class_1.prototype, "config", {
        get: function () {
            var coresConfig = this.taphomeCores.map(function (core) { return core.config; }).join("");
            if (!coresConfig) {
                return "";
            }
            return "taphome:\n  cores:\n" + coresConfig;
        },
        enumerable: false,
        configurable: true
    });
    return class_1;
}());
var viewModel = new ViewModel();
var app = new Vue({
    el: "#app",
    data: viewModel,
    methods: {
        copyConfig: function () {
            var copyTextarea = document.getElementById('config-textarea');
            copyTextarea.focus();
            copyTextarea.select();
            document.execCommand('copy');
        },
        addCore: function () {
            viewModel.addCore();
        }
    },
    computed: {
        config: {
            get: function () {
                return viewModel.config;
            },
            set: function (yaml) {
                viewModel.loadFromConfig(yaml);
                return viewModel.config;
            },
        },
    },
});
