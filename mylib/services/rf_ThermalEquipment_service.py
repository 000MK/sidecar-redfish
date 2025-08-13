'''
這是Redfish的chassis service
'''
import os, re, time
import requests
from enum import Enum
from typing import Optional, Literal
from datetime import datetime
from http import HTTPStatus
from load_env import hardware_info, sensor_info, redfish_info
from mylib.common.proj_error import ProjError
from mylib.models.rf_sensor_model import (
    RfSensorCollectionModel, 
    RfSensorModel, 
)
from mylib.services.base_service import BaseService
from mylib.models.rf_environment_metrics_model import RfEnvironmentMetricsModel
from mylib.models.rf_leak_detector import RfLeakDetectorModel
from mylib.models.rf_status_model import RfStatusModel
# from mylib.models.rf_primary_coolant_connector_model import RfPrimaryCoolantConnectorCollectionModel, RfPrimaryCoolantConnectorModel
# from mylib.models.rf_Secondary_coolant_connector_model import RfSecondaryCoolantConnectorCollectionModel, RfSecondaryCoolantConnectorModel
from mylib.models.rf_cdu_model import RfCduModel, RfCduCollectionModel
from mylib.models.rf_cooling_loop_model import RfCoolantModel, RfCoolantType
from mylib.models.rf_pump_collection_model import RfPumpCollectionModel
from mylib.models.rf_pump_model import RfPumpModel
from mylib.utils.JsonUtil import JsonUtil
from mylib.utils.load_api import load_raw_from_api, CDU_BASE
from mylib.models.rf_sensor_model import RfSensorPumpExcerpt
from mylib.models.rf_control_model import RfControlSingleLoopExcerptModel
from mylib.models.rf_filter_model import RfFilterModel
from mylib.models.rf_filter_collection_model import RfFilterCollectionModel
from mylib.models.rf_leak_detection_model import RfLeakDetectionModel
from mylib.models.rf_leak_detector_id import RfLeakDetectionIdModel
from mylib.common.proj_error import ProjRedfishError, ProjRedfishErrorCode
from mylib.models.rf_coolant_connector_model import RfCoolantConnectorModel, RfCoolantConnectorCollectionModel
# from mylib.routers.Chassis_router import GetControlMode
from mylib.utils.controlUtil import GetControlMode
from mylib.utils.StatusUtil import StatusUtil
from mylib.utils.controlUtil import ControlMode_change
from mylib.utils.system_info import get_uptime
from mylib.common.proj_constant import ProjNames
from mylib.utils.DateTimeUtil import DateTimeUtil


class CoolantConnectorEnums(str, Enum):
    # must match the name in hardware_info.yaml
    PRIMARY = "PrimaryCoolantConnectors" 
    SECONDARY = "SecondaryCoolantConnectors"

class RfThermalEquipmentService(BaseService):
    class PrimaryCoolantConnectorCollectionModel(RfCoolantConnectorCollectionModel):
        def __init__(self, cdu_id: str, **kwargs):
            super().__init__(cdu_id=cdu_id, **kwargs)
            # self.odata_type = "#CoolantConnectorCollection.CoolantConnectorCollection"
            self.Name = "Primary (supply side) Cooling Loop Connection Collection"
            self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors"
            
            member_cnt = int(os.environ.get('REDFISH_PRIMARYCOOLANTCONNECTOR_COLLECTION_CNT', 0))
            for sn in range(1, member_cnt + 1):
                self.Members.append({"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors/{sn}"})
            self.Members_odata_count = member_cnt
    
    class SecondaryCoolantConnectorCollectionModel(RfCoolantConnectorCollectionModel):
        def __init__(self, cdu_id: str, **kwargs):
            super().__init__(cdu_id=cdu_id, **kwargs)
            # self.odata_type = "#CoolantConnectorCollection.CoolantConnectorCollection"
            self.Name = "Secondary (supply side) Cooling Loop Connection Collection"
            self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors"
            
            member_cnt = int(os.environ.get('REDFISH_SECONDARYCOOLANTCONNECTOR_COLLECTION_CNT', 0))
            for sn in range(1, member_cnt + 1):
                self.Members.append({"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors/{sn}"})
            self.Members_odata_count = member_cnt
        
    class PrimaryCoolantConnectorModel(RfCoolantConnectorModel):
        def __init__(self, cdu_id: str, coolant_connector_id: str, **kwargs):
            super().__init__(cdu_id=cdu_id, coolant_connector_id=coolant_connector_id, **kwargs)
            self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors/{coolant_connector_id}"
            self.Name = "Mains Input from Chiller"
            self.Description = "Primary input from facility chiller (no valve control)"

    class SecondaryCoolantConnectorModel(RfCoolantConnectorModel):
        def __init__(self, cdu_id: str, coolant_connector_id: str, **kwargs):
            super().__init__(cdu_id=cdu_id, coolant_connector_id=coolant_connector_id, **kwargs)
            self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors/{coolant_connector_id}"
            self.Name = f"SecondaryCoolantConnector{coolant_connector_id}"
            self.Description = "Secondary input from facility chiller"


    def fetch_CDUs(self, cdu_id: Optional[str] = None) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/1"

        :param cdu_id: str
        :return: dict
        """
        if cdu_id is None:
            m = RfCduCollectionModel()
        else:
            m = RfCduModel(
                cdu_id=cdu_id,
                **hardware_info["CDU"]
            )
            m.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}"
            m.Description = f"Cooling Distribution Unit #{cdu_id}, designed for liquid cooling of chassis systems."
            m.Filters = {
                "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters"
            }
            m.PrimaryCoolantConnectors = {
                "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors"
            }
            # self.SecondaryCoolantConnectors = {
            #     "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors"
            # }
            m.Pumps = {
                "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps"
            }
            m.LeakDetection = {
                "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/LeakDetection"
            }
            # m.Coolant = {
            #     "CoolantType": "Water",
            #     "DensityKgPerCubicMeter": 1030, 
            #     "SpecificHeatkJoulesPerKgK": 3900,
            # } # Impl. in _config_cdu_model()
            m.EnvironmentMetrics = {
                "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/EnvironmentMetrics"
            }
            m.Actions = {
                "#CoolingUnit.SetMode": {
                    "target": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Actions/CoolingUnit.SetMode",
                    "Mode@Redfish.AllowableValues": [
                        "Enabled",
                        "Disabled"
                    ]
                }
            }
            m.Links = {
                "Chassis": [
                    {
                        "@odata.id": f"/redfish/v1/Chassis/{sn}"
                    }
                    for sn in range(1, int(os.environ.get('REDFISH_CHASSIS_COLLECTION_CNT', 1)) + 1)
                ],
                "ManagedBy": [
                    {
                        "@odata.id": "/redfish/v1/Managers/CDU"
                    }
                ]
            }
            datetime_format = os.getenv("DATETIME_FORMAT", "%Y-%m-%dT%H:%M:%SZ")
            m.ProductionDate = DateTimeUtil.format_string(datetime_format)
            
            status = {
                "State": "Enabled",
                "Health": "OK"
            }
            m.Status = RfStatusModel.from_dict(status)
            m.FirmwareVersion = self._read_version_from_cache()["version"]["WebUI"]
            m.Version = self._read_version_from_cache()["fw_info"]["Version"]
            m.SerialNumber = self._read_version_from_cache()["fw_info"]["SN"]
            m.CoolingCapacityWatts = hardware_info.get("CDU", {}).get("CoolingCapacityWatts", -1)
            m.Oem = {}
            m = self._config_cdu_model(m)
            
        return m.to_dict()
    
    def fetch_CDUs_SetMode(self, cdu_id: str, body: dict) -> dict:
        ControlMode = body["Mode"]
        if ControlMode == "Enabled": 
            ControlMode = "auto"
        else:
            ControlMode = "stop"    
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json={"mode": ControlMode},  
                timeout=3
            )
            r.raise_for_status()
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.INTERNAL_ERROR,
                message=f"PATCH {CDU_BASE}/api/v1/cdu/status/op_mode FAIL: details={str(e)}"
            )

        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            # return {
            #     "error": "Forwarding to the CDU control service failed",
            #     "details": str(e)
            # }, 502
            raise ProjRedfishError(
                ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE, 
                f"Forwarding to the CDU control service failed: {str(e)}"
            )
        return body, 200
    
    def fetch_CDUs_EnvironmentMetrics(self, cdu_id: str) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/1/EnvironmentMetrics"

        :param cdu_id: str
        :return: dict
        """
        m = RfEnvironmentMetricsModel(cdu_id=cdu_id)
        boot_time_h = get_uptime()[0]
        # print(f"CDU boot time: {boot_time_h} hours")
        m.TemperatureCelsius["Reading"] = self._read_reading_value_by_sensor_id("TemperatureCelsius")
        m.DewPointCelsius["Reading"] = self._read_reading_value_by_sensor_id("DewPointCelsius")
        m.HumidityPercent["Reading"] = self._read_reading_value_by_sensor_id("HumidityPercent")
        m.PowerWatts["Reading"] = self._read_reading_value_by_sensor_id("PowerConsume")
        m.EnergykWh["Reading"] = round(self._read_reading_value_by_sensor_id("PowerConsume") * boot_time_h / 1000, 2)
        
        # m.AbsoluteHumidity["Reading"] = self._read_reading_value_by_sensor_id("AbsoluteHumidity")
        return m.to_dict()
    
    def fetch_CDUs_LeakDetection(self, cdu_id: str) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/1/LeakDetection"

        :param cdu_id: str
        :return: dict
        """
        leakgroup = [
            {
                "GroupName": "LeakDetectorGroup1",
                "Detectors": [
                    {"DataSourceUri":   "/redfish/v1/ThermalEquipment/CDUs/1/LeakDetection/LeakDetectors/1",}
                ],
                # 必要
                "HumidityPercent": {
                    "DataSourceUri": "/redfish/v1/Chassis/1/Sensors/HumidityPercent",
                    "Reading": self._read_reading_value_by_sensor_id("HumidityPercent")
                },
                # "Status": {
                #     "State": "Enabled",
                #     "Health": "OK"
                # },
                "Status": self._read_leak_detector_status("leak_detector")
            }
        ]
        
        m = RfLeakDetectionModel(cdu_id=cdu_id)
        m.Status = self._read_leak_detector_status("leak_detector")
        m.LeakDetectorGroups = leakgroup
        m.LeakDetectors = {
            "@odata.id": "/redfish/v1/ThermalEquipment/CDUs/1/LeakDetection/LeakDetectors"
        }
        
        return m.to_dict()
    
    def fetch_CDUs_LeakDetection_LeakDetectors(self, cdu_id: str) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/1/LeakDetection/LeakDetectors"
        Response Example:
        {
            "@odata.id": "/redfish/v1/ThermalEquipment/CDUs/1/LeakDetection/LeakDetectors",
            "@odata.type": "#LeakDetectors.v1_3_0.LeakDetectors",
            "Id": "1",
            "Name": "LeakDetectors",
            "Status": {
                "State": "Enabled",
                "Health": "Critical"
            },
        }

        :param cdu_id: str
        """
        m = RfLeakDetectorModel(cdu_id=cdu_id)
        # m.Status = self._read_leak_detector_status()
        return m.to_dict()

    def fetch_CDUs_LeakDetection_LeakDetectors_id(self, cdu_id: str, leak_detector_id: str) -> dict:
        m = RfLeakDetectionIdModel(cdu_id=cdu_id, leak_detector_id=leak_detector_id)
        
        # leak_mapping = {
        #     "Device1" : "leak_detector",
        #     "Rack1" : "rack_leak_detector_1",
        #     "Rack2" : "rack_leak_detector_2",
        # }
        
        # leak_mapping_result = leak_mapping.get(leak_detector_id)
        leak_switch = self._build_leakdetectors_id(cdu_id, leak_detector_id)
        if leak_switch is not None:
            if leak_switch is not True:
                return f"{leak_detector_id} not enabled"
        
        leak_mapping_result = hardware_info.get("leak_detectors").get(leak_detector_id).get("RestName")
        # status
        m.Status = self._read_leak_detector_status(leak_mapping_result)
        m.DetectorState = m.Status.Health
        return m.to_dict()

    def _read_reading_value_by_sensor_id(self, sensor_id: str) -> float:
        """
        @return Reading & ReadingUnits
        """
        # id_readingInfo_map = {
        #     "PrimaryFlowLitersPerMinute": {
        #         "ReadingUnits": "L/min", 
        #         "fieldNameToFetchSensorValue": "coolant_flow_rate"
        #     },
        #     "PrimaryHeatRemovedkW": {
        #         "ReadingUnits": "kW", 
        #         "fieldNameToFetchSensorValue": "heat_capacity"
        #     },
        #     "PrimarySupplyTemperatureCelsius": {
        #         "ReadingUnits": "Celsius", 
        #         "fieldNameToFetchSensorValue": "temp_coolant_supply"
        #     },
        #     "PrimaryReturnTemperatureCelsius": {
        #         "ReadingUnits": "Celsius", 
        #         "fieldNameToFetchSensorValue": "temp_coolant_return"
        #     }, 
        #     "PrimaryDeltaTemperatureCelsius": {
        #         "ReadingUnits": "Celsius", 
        #         "fieldNameToFetchSensorValue": "temp_coolant_supply,temp_coolant_return"
        #     },
        #     "PrimarySupplyPressurekPa": {
        #         "ReadingUnits": "kPa", 
        #         "fieldNameToFetchSensorValue": "pressure_coolant_supply"
        #     },
        #     "PrimaryReturnPressurekPa": {
        #         "ReadingUnits": "kPa", 
        #         "fieldNameToFetchSensorValue": "pressure_coolant_return"
        #     },
        #     "PrimaryDeltaPressurekPa": {
        #         "ReadingUnits": "kPa", 
        #         "fieldNameToFetchSensorValue": "pressure_coolant_supply,pressure_coolant_return"
        #     },
        #     "TemperatureCelsius": {
        #         "ReadingUnits": "Celsius", 
        #         "fieldNameToFetchSensorValue": "temperature_ambient"
        #     },
        #     "DewPointCelsius": {
        #         "ReadingUnits": "Celsius", 
        #         "fieldNameToFetchSensorValue": "temperature_dew_point"
        #     },
        #     "HumidityPercent": {
        #         "ReadingUnits": "Percent", 
        #         "fieldNameToFetchSensorValue": "humidity_relative"
        #     },
        #     "WaterPH": {
        #         "ReadingUnits": "pH", 
        #         "fieldNameToFetchSensorValue": "ph_level"
        #     },
        #     "Conductivity": {
        #         "ReadingUnits": "μs/cm", 
        #         "fieldNameToFetchSensorValue": "conductivity"
        #     },
        #     "Turbidity": {
        #         "ReadingUnits": "NTU", 
        #         "fieldNameToFetchSensorValue": "turbidity"
        #     },
        #     "PowerConsume": {
        #         "ReadingUnits": "kW", 
        #         "fieldNameToFetchSensorValue": "power_total"
        #     },
        # }
        id_readingInfo_map = sensor_info["id_readingInfo_map"]
        reading_info = id_readingInfo_map.get(sensor_id, {})
        if reading_info:
            sensor_value_json = self._read_components_chassis_summary_from_cache()
            reading_info["Reading"] = self._calc_delta_value(sensor_value_json, reading_info["fieldNameToFetchSensorValue"])
        else:
            reading_info["Reading"] = 0.0
        return reading_info["Reading"]
    
    def _load_reading_info_by_sensor_id(self, sensor_id: str) -> dict:
        """
        @return Reading & ReadingUnits
        @note api response from /cdu/status/sensor_value is
            {
                "temp_coolant_supply": 0,
                " temp_coolant_supply_spare": 0,
                "temp_coolant_return": 0,
                "temp_coolant_return_spare": 0,
                "pressure_coolant_supply": -125,
                "pressure_coolant_supply_spare": -125,
                "pressure_coolant_return": -125,
                "pressure_coolant_return_spare": -125,
                "pressure_filter_in": -125,
                "pressure_filter_out": -125,
                "coolant_flow_rate": -70,
                "temperature_ambient": 0,
                "humidity_relative": 0,
                "temperature_dew_point": 0,
                "ph_level": 0,
                "conductivity": 0,
                "turbidity": 0,
                "power_total": 0,
                "cooling_capacity": 0,
                "heat_capacity": 0,
                "fan1_speed": 0,
                "fan2_speed": 0,
                "fan3_speed": 0,
                "fan4_speed": 0,
                "fan5_speed": 0,
                "fan6_speed": 0,
                "fan7_speed": 0,
                "fan8_speed": 0
            }
        """
        id_readingInfo_map = sensor_info["id_readingInfo_map"]

        # 動態調整風扇數量
        fan_cnt = len(hardware_info.get("Fans", "")) 
        for i in range(fan_cnt):
            id_readingInfo_map[f"Fan{i+1}"] = {
                "ReadingUnits": "%", 
                "fieldNameToFetchSensorValue": f"fan{i+1}"
            }
            
        reading_info = id_readingInfo_map.get(sensor_id)
        if reading_info:
            sensor_value_json = self._read_components_chassis_summary_from_cache()
            if reading_info['fieldNameToFetchSensorValue'] == "EnergykWh":
                boot_time_h = get_uptime()[0]
                EnergykWh_data = self._calc_delta_value_status(sensor_value_json, "power_total")
                reading_info["Reading"] = round(EnergykWh_data[0] * boot_time_h / 1000, 2)
                reading_info["Status"] = EnergykWh_data[1]
            else:
                reading_info["Reading"], reading_info["Status"] = self._calc_delta_value_status(sensor_value_json, reading_info["fieldNameToFetchSensorValue"])
        else:
            reading_info = {}
            reading_info["Reading"] = -1  
        return reading_info    
    
    def _read_leak_detector_status(self, leak_detector_id: str) -> RfStatusModel:
        """
        目前的設計：UI會讀web app的/get_data，js判斷如下
            if (data["error"]["leakage1_broken"]) {
                $("#leakage1")
                    .css("color", "red")
                    .text("Broken");
            } else if (
                !data["error"]["leakage1_broken"] &&
                data["error"]["leakage1_leak"]
            ) {
                $("#leakage1").css("color", "red").text("Leak");
            } else {
                $("#leakage1").css("color", "black").text("OK");
            }
        以上直接去讀 {project_root}/webUI/web/json/sensor_data.json的`error`欄位
        (註) 20250505 如果未來webUI和redfish佈署在不同機器，直接讀json檔是不通的。
        (註) 20250509 改統一由RestAPI取資料
        (註) 20250701 改使用leak_detector_id指定取得檢測器的狀態
        """
        ret_status_model = None
        try:
            summary_json = self._read_components_thermal_equipment_summary_from_cache()
            leak_detector_info = summary_json[leak_detector_id]
            ret_status_model = RfStatusModel.from_dict(leak_detector_info["status"])
        except Exception as e:
            print(e)
            ret_status_model = RfStatusModel.from_dict({"State": "Disabled", "Health": "Critical"})
        return ret_status_model
            
    # def _read_oem_by_cdu_id(self, cdu_id: str):
    #     return self._read_components_thermal_equipment_summary_from_cache().get("Oem")
        
    
    def fetch_CDUs_PrimaryCoolantConnectors(self, cdu_id: str) -> dict:
        """
        對應 "/ThermalEquipment/CDUs/1/PrimaryCoolantConnectors"

        :param cdu_id: str
        :return: dict
        """
        m = self.PrimaryCoolantConnectorCollectionModel(cdu_id=cdu_id)
        return m.to_dict()
    
    def build_CoolantConnectorModel(self, cdu_id: str, coolant_connector_id: str, key: Literal["PrimaryCoolantConnectors", "SecondaryCoolantConnectors"]) -> RfCoolantConnectorModel:
        """
        對應 
            "/ThermalEquipment/CDUs/1/PrimaryCoolantConnectors/1"
            "/ThermalEquipment/CDUs/1/SecondaryCoolantConnectors/1"
        :param cdu_id: str
        :param coolant_connector_id: str
        :param key: str, PrimaryCoolantConnectors or SecondaryCoolantConnectors in hardware_info.yaml
        :return: dict
        """
        m = None
        # TODO: 未來可以考慮使用 factory pattern. Not not to over-engineering
        if key == CoolantConnectorEnums.PRIMARY:
            m = self.PrimaryCoolantConnectorModel(cdu_id=cdu_id, coolant_connector_id=coolant_connector_id)
        elif key == CoolantConnectorEnums.SECONDARY:
            m = self.SecondaryCoolantConnectorModel(cdu_id=cdu_id, coolant_connector_id=coolant_connector_id)
        else:
            raise ProjError(HTTPStatus.BAD_REQUEST, f"Invalid key: {key}")
        hardware_info_by_id = hardware_info.get(key).get(coolant_connector_id)
        
        # m = self.PrimaryCoolantConnectorModel(cdu_id=cdu_id, coolant_connector_id=primary_coolant_connector_id)
        # value_all = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/sensor_value")
        # pump_swap_time = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/control/pump_swap_time")
        op_mode = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")
        
        m.RatedFlowLitersPerMinute = hardware_info_by_id.get("RatedFlowLitersPerMinute")
        m.Coolant = hardware_info_by_id.get("Coolant")
        m.CoolantConnectorType = hardware_info_by_id.get("CoolantConnectorType")
       
        all_status_list = []
        # Sensors
        sensors_map = hardware_info_by_id.get("Sensors")
        for sensor_name in sensors_map.keys():
            sensor_data = self._load_reading_info_by_sensor_id(sensor_name)
            field_name = hardware_info_by_id.get("Sensors").get(sensor_name)
            tmp = {
                "DataSourceUri": f"/redfish/v1/Chassis/1/Sensors/{sensor_name}",
                "Reading": sensor_data.get("Reading"),
            }
                
            setattr(m, field_name, tmp)  
            status_data = sensor_data.get("Status")
            all_status_list.append(status_data)  
            
        # m.Oem = self._build_oem_for_PrimaryCoolantConnectorModel(m)
        m.Oem = None # should be impl. by child class
            
        ControlMode = GetControlMode()
        m.SupplyTemperatureControlCelsius = {
            "SetPoint": op_mode.get("temp_set"),
            "AllowableMax": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.max"),
            "AllowableMin": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.min"),
            "ControlMode": ControlMode,
        }
        m.DeltaPressureControlkPa = {
            "SetPoint": op_mode.get("pressure_set"),
            "AllowableMax": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.max"),
            "AllowableMin": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.min"),
            "ControlMode": ControlMode,
        }

        # m.Status = RfStatusModel.from_dict({"State": "Enabled", "Health": "OK"}) # 未動態
        worst_status = StatusUtil.get_worst_health_dict(all_status_list)
        m.Status = RfStatusModel.from_dict(worst_status)
        return m

    def fetch_CDUs_PrimaryCoolantConnectorsId(self, cdu_id: str, primary_coolant_connector_id: str) -> dict:
        """
        對應 "/ThermalEquipment/CDUs/1/PrimaryCoolantConnectors/1"

        :param cdu_id: str
        :param primary_coolant_connector_id: str
        :return: dict
        """
        # m = self.PrimaryCoolantConnectorModel(cdu_id=cdu_id, coolant_connector_id=primary_coolant_connector_id)
        # # value_all = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/sensor_value")
        # # pump_swap_time = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/control/pump_swap_time")
        # op_mode = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")

        
        # m.RatedFlowLitersPerMinute = hardware_info.get("PrimaryCoolantConnectors").get(primary_coolant_connector_id).get("RatedFlowLitersPerMinute")
        # m.Coolant = hardware_info.get("PrimaryCoolantConnectors").get(primary_coolant_connector_id).get("Coolant")
        # m.CoolantConnectorType = hardware_info.get("PrimaryCoolantConnectors").get(primary_coolant_connector_id).get("CoolantConnectorType")
       
        
        # # Sensors
        # sensors_map = hardware_info.get("PrimaryCoolantConnectors").get(primary_coolant_connector_id).get("Sensors")
        # for sensor_name in sensors_map.keys():
        #     sensor_data = self._load_reading_info_by_sensor_id(sensor_name)
        #     field_name = hardware_info.get("PrimaryCoolantConnectors").get(primary_coolant_connector_id).get("Sensors").get(sensor_name)
        #     tmp = {
        #         "DataSourceUri": f"/redfish/v1/Chassis/1/Sensors/{sensor_name}",
        #         "Reading": sensor_data.get("Reading"),
        #     }
                
        #     setattr(m, field_name, tmp)  
            
        # m.Oem = self._build_oem_for_PrimaryCoolantConnectorModel(m)
            
        # ControlMode = GetControlMode()
        # m.SupplyTemperatureControlCelsius = {
        #     "SetPoint": op_mode.get("temp_set"),
        #     "AllowableMax": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.max"),
        #     "AllowableMin": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.min"),
        #     "ControlMode": ControlMode,
        # }
        # m.DeltaPressureControlkPa = {
        #     "SetPoint": op_mode.get("pressure_set"),
        #     "AllowableMax": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.max"),
        #     "AllowableMin": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.min"),
        #     "ControlMode": ControlMode,
        # }

        # m.Status = RfStatusModel.from_dict({"State": "Enabled", "Health": "OK"}) # 未動態
        
        # return m.to_dict()
        raise NotImplementedError

    def patch_CDUs_PrimaryCoolantConnectorsId(self, cdu_id: str, primary_coolant_connector_id: str, body: dict):
        temp_setpoint = body.get("SupplyTemperatureControlCelsius", {}).get("SetPoint")
        temp_controlmode = body.get("SupplyTemperatureControlCelsius", {}).get("ControlMode")
        pressure_setpoint = body.get("DeltaPressureControlkPa", {}).get("SetPoint")
        pressure_controlmode = body.get("DeltaPressureControlkPa", {}).get("ControlMode")
        pump_swap_time = body.get("Oem",{}).get("Supermicro", {}).get("PumpSwapTime")
        
        automatic_setting = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")
        # 空白 邏輯判斷
        if temp_setpoint is None:
            temp_setpoint = automatic_setting["temp_set"]
        if pressure_setpoint is None:
            pressure_setpoint = automatic_setting["pressure_set"]
        # controlmode判斷 
        if temp_controlmode is None and pressure_controlmode is None:
            controlmode = automatic_setting["mode"]
            controlmode = ControlMode_change(controlmode)
        elif  temp_controlmode is None: 
            controlmode = pressure_controlmode
        elif pressure_controlmode is None:
            controlmode = temp_controlmode
        else:
            controlmode = temp_controlmode    
        if temp_controlmode != pressure_controlmode:    
            controlmode = automatic_setting["mode"]
            controlmode = ControlMode_change(controlmode)
        # if pump_swap_time is not None:
        #     pump_swap_time = tmp    
        controlmode = ControlMode_change(controlmode)
        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json={"mode": controlmode, "temp_set": temp_setpoint, "pressure_set": pressure_setpoint, "pump_swap_time": pump_swap_time},
                timeout=3
            )
            r.raise_for_status()
            
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                ProjRedfishErrorCode.INTERNAL_ERROR, 
                f"PATCH {CDU_BASE}/api/v1/cdu/status/op_mode FAIL: details={str(e)}"
            )

        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            # return {
            #     "error": "Forwarding to the CDU control service failed",
            #     "details": str(e)
            # }, 502
            raise ProjRedfishError(
                ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE, 
                f"Forwarding to the CDU control service failed: {str(e)}"
            )
        time.sleep(2) # 等待RestAPI回應
        return self.fetch_CDUs_PrimaryCoolantConnectorsId(cdu_id, primary_coolant_connector_id)
        
    def fetch_CDUs_SecondaryCoolantConnectors(self, cdu_id: str) -> dict:   
        
        m = self.SecondaryCoolantConnectorCollectionModel(cdu_id=cdu_id)
        return m.to_dict()
    
    def fetch_CDUs_SecondaryCoolantConnectorsId(self, cdu_id: str, secondray_coolant_connector_id: str) -> dict:
        """
        對應 "/ThermalEquipment/CDUs/1/SecondaryCoolantConnectors/1"

        :param cdu_id: str
        :param secondray_coolant_connector_id: str
        :return: dict
        """
        # m = self.SecondaryCoolantConnectorModel(cdu_id=cdu_id, coolant_connector_id=secondray_coolant_connector_id)
        # # value_all = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/sensor_value")
        # # pump_swap_time = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/control/pump_swap_time")
        # op_mode = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")

        
        # m.RatedFlowLitersPerMinute = hardware_info.get("SecondaryCoolantConnectors").get(secondray_coolant_connector_id).get("RatedFlowLitersPerMinute")
        # m.Coolant = hardware_info.get("SecondaryCoolantConnectors").get(secondray_coolant_connector_id).get("Coolant")
        # m.CoolantConnectorType = hardware_info.get("SecondaryCoolantConnectors").get(secondray_coolant_connector_id).get("CoolantConnectorType")
       
        
        # # Sensors
        # sensors_map = hardware_info.get("SecondaryCoolantConnectors").get(secondray_coolant_connector_id).get("Sensors")
        # for sensor_name in sensors_map.keys():
        #     sensor_data = self._load_reading_info_by_sensor_id(sensor_name)
        #     field_name = hardware_info.get("SecondaryCoolantConnectors").get(secondray_coolant_connector_id).get("Sensors").get(sensor_name)
        #     tmp = {
        #         "DataSourceUri": f"/redfish/v1/Chassis/1/Sensors/{sensor_name}",
        #         "Reading": sensor_data.get("Reading"),
        #     }
                
        #     setattr(m, field_name, tmp)  
            
        # # m.Oem = self._build_oem_for_PrimaryCoolantConnectorModel(m)
            
        # ControlMode = GetControlMode()
        # m.SupplyTemperatureControlCelsius = {
        #     "SetPoint": op_mode.get("temp_set"),
        #     "AllowableMax": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.max"),
        #     "AllowableMin": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.min"),
        #     "ControlMode": ControlMode,
        # }
        # m.DeltaPressureControlkPa = {
        #     "SetPoint": op_mode.get("pressure_set"),
        #     "AllowableMax": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.max"),
        #     "AllowableMin": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.min"),
        #     "ControlMode": ControlMode,
        # }

        # m.Status = RfStatusModel.from_dict({"State": "Enabled", "Health": "OK"}) # 未動態
        
        # return m.to_dict()
        raise NotImplementedError
    
    def patch_CDUs_SecondaryCoolantConnectorsId(self, cdu_id: str, secondray_coolant_connector_id: str, body: dict):
        temp_setpoint = body.get("SupplyTemperatureControlCelsius", {}).get("SetPoint")
        temp_controlmode = body.get("SupplyTemperatureControlCelsius", {}).get("ControlMode")
        pressure_setpoint = body.get("DeltaPressureControlkPa", {}).get("SetPoint")
        pressure_controlmode = body.get("DeltaPressureControlkPa", {}).get("ControlMode")
        
        automatic_setting = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")
        # 空白 邏輯判斷
        if temp_setpoint is None:
            temp_setpoint = automatic_setting["temp_set"]
        if pressure_setpoint is None:
            pressure_setpoint = automatic_setting["pressure_set"]
        # controlmode判斷 
        if temp_controlmode is None and pressure_controlmode is None:
            controlmode = automatic_setting["mode"]
            controlmode = ControlMode_change(controlmode)
        elif  temp_controlmode is None: 
            controlmode = pressure_controlmode
        elif pressure_controlmode is None:
            controlmode = temp_controlmode
        else:
            controlmode = temp_controlmode    
        if temp_controlmode != pressure_controlmode:    
            controlmode = automatic_setting["mode"]
            controlmode = ControlMode_change(controlmode)
        # if pump_swap_time is not None:
        #     pump_swap_time = tmp    
        controlmode = ControlMode_change(controlmode)
        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json={"mode": controlmode, "temp_set": temp_setpoint, "pressure_set": pressure_setpoint},
                timeout=3
            )
            r.raise_for_status()
            
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                ProjRedfishErrorCode.INTERNAL_ERROR, 
                f"PATCH {CDU_BASE}/api/v1/cdu/status/op_mode FAIL: details={str(e)}"
            )

        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            # return {
            #     "error": "Forwarding to the CDU control service failed",
            #     "details": str(e)
            # }, 502
            raise ProjRedfishError(
                ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE, 
                f"Forwarding to the CDU control service failed: {str(e)}"
            )
        time.sleep(2) # 等待RestAPI回應
        return self.fetch_CDUs_SecondaryCoolantConnectorsId(cdu_id, secondray_coolant_connector_id)
    
    def fetch_CDUs_Pumps(self, cdu_id: str) -> dict:
        """
        對應 "/ThermalEquipment/CDUs/1/Pumps"

        :param cdu_id: str
        :return: dict
        """
        m = RfPumpCollectionModel(cdu_id=cdu_id)
        # for i in range(m.Members_odata_count):
        #     m.Members.append({
        #         "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{i+1}"
        #     })
        return m.to_dict()
    
    def fetch_CDUs_Pumps_Pump_get(self, cdu_id: str, pump_id: str) -> dict:
        """
        對應 "/ThermalEquipment/CDUs/<cdu_id>/Pumps/<pump_id>"

        :param cdu_id: str
        :param pump_id: str
        :return: dict
        """
        pump_max_speed = 16000  # 最大速度為16000 RPM
        m = RfPumpModel(cdu_id=cdu_id, pump_id=pump_id)
        # speed
        pump_speed = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/pump_speed")[f"pump{pump_id}_speed"]
        m.PumpSpeedPercent = RfSensorPumpExcerpt(**{
            "Reading": pump_speed,
            "SpeedRPM": pump_speed * pump_max_speed / 100            
        })
        # control
        m.SpeedControlPercent = RfControlSingleLoopExcerptModel(**{
            "SetPoint": load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/control/pump_speed")[f"pump{pump_id}_speed"],  
            "AllowableMin": hardware_info["Pumps"][pump_id]["AllowableMin"],
            "AllowableMax": hardware_info["Pumps"][pump_id]["AllowableMax"],
            "ControlMode": GetControlMode()  
        })
        # status
        state = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/pump_state")[f"pump{pump_id}_state"]
        health = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/pump_health")[f"pump{pump_id}_health"]
        # print(f"state: {state}, health: {health}")
        if state == "Disable": state = "Disabled"
        if state == "Enable": state = "Enabled"
        if health == "Error": health = "Critical"
        status = {
            "State": state,
            "Health": health
        }
        m.Status = RfStatusModel.from_dict(status)
        # service time
        service_hours = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/pump_service_hours")[f"pump{pump_id}_service_hours"]
        m.ServiceHours = service_hours
        # location
        # m.Location = hardware_info["Pumps"][pump_id]["Location"]
        # oem
        m.Oem = {
            "Supermicro": {
                f"Inventer {pump_id} MC": {
                    "@odata.type": "#Supermicro.Inventer.v1_0_0.Inventer",
                    "PowerStatus": "OFF"
                }
            }        
        }

        return m.to_dict()
    
    def fetch_CDUs_Pumps_Pump_patch(self, cdu_id: str, pump_id: str, body: dict) -> dict:
        """
        對應 "/ThermalEquipment/CDUs/<cdu_id>/Pumps/<pump_id>"

        :param cdu_id: str
        :param pump_id: str
        :param body: dict
        :return: dict
        """
        m = RfPumpModel(cdu_id=cdu_id, pump_id=pump_id)
        pump_setpoint = body["SpeedControlPercent"]['SetPoint']
        pump_controlmode = body["SpeedControlPercent"]['ControlMode']
        pump_controlmode = ControlMode_change(pump_controlmode)
        body["SpeedControlPercent"]['ControlMode'] = pump_controlmode
        # 驗證範圍
        scp = hardware_info["Pumps"][pump_id]
        if not (scp["AllowableMin"] <= pump_setpoint <= scp["AllowableMax"]) and pump_setpoint != 0:
            # return {
            #     "error": f"pump_speed needs to be between {scp['AllowableMin']} and {scp['AllowableMax']} or 0"
            # }, 400
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.GENERAL_ERROR,
                message=f"pump_speed needs to be between {scp['AllowableMin']} and {scp['AllowableMax']} or 0"
            )
            
        payload = self._build_pumps_patch_payload(cdu_id, pump_id, body)
        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json= payload, #{"mode": pump_controlmode, "pump_speed": pump_setpoint},
                timeout=5
            )
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.INTERNAL_ERROR,
                message=f"PATCH {CDU_BASE}/api/v1/cdu/status/op_mode FAIL: details={str(e)}"
            )

        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            # return {
            #     "error": "Forwarding to the CDU control service failed",
            #     "details": str(e)
            # }, 502  
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE,
                message=f"Forwarding to the CDU control service failed: {str(e)}"
            )  
        
        # 更新內存資料
        # m.SpeedControlPercent = RfControlSingleLoopExcerptModel(**{
        #     "SetPoint": pump_setpoint, #if new_sw else 0,
        #     "AllowableMin": scp["AllowableMin"],
        #     "AllowableMax": scp["AllowableMax"],
        #     "ControlMode": ControlMode_change(pump_controlmode)
        # })
        # m.Oem["Supermicro"][f"Inventer {pump_id} MC"]["Switch"] = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/mc")[f"mc{pump_id}_sw"]
        # return m.to_dict(), 200
        # 因為儲存時間問題setpoint無法即時更新
        time.sleep(2)
        return self.fetch_CDUs_Pumps_Pump_get(cdu_id, pump_id), 200
    
    def fetch_CDUs_Filters(self, cdu_id: str) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/<cdu_id>/Filters"

        :param cdu_id: str
        :return: dict
        """
        m = RfFilterCollectionModel(cdu_id=cdu_id)
        return m.to_dict()
    
    def fetch_CDUs_Filters_id(self, cdu_id: str, filter_id: str) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/<cdu_id>/Filters/<filter_id>"

        :param cdu_id: str
        :param filter_id: str
        :return: dict
        
        @note 
            p3, p4其中一個broken他就broken
            warning, alert抓p4
        """
        m = RfFilterModel(cdu_id=cdu_id, filter_id=filter_id)

        m.HotPluggable = hardware_info["Filters"][filter_id]["HotPluggable"]
        
        # ServicedDate
        m.ServicedDate = hardware_info["Filters"][filter_id]["ServicedDate"]
        # TODO: use SensorAPIAdapter instead
        # m.ServiceHours = int(load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/thermal_equipment/summary").get("Filter_run_time", -1))
        
        # location
        # raw_location = hardware_info["Filters"][filter_id]["Location"]
        # m.Location = RfLocationModel(raw_location)
        
        # Status
        
        health_data, ServiceHours = self._build_filter(cdu_id, filter_id)
        m.ServiceHours = ServiceHours
        status = StatusUtil().get_worst_health_dict(health_data)
        # print("health: ", health)
        # state = "Enabled" if health is "OK" else "Disabled"
        # status = {
        #     "State": state,
        #     "Health": health
        # }
        m.Status = RfStatusModel.from_dict(status)

        return m.to_dict(), 200
    
    
    def fetch_CDUs_Pumps_SetMode(self, cdu_id: str, pump_id: str, body: dict) -> dict:
        """
        對應 "/redfish/v1/ThermalEquipment/CDUs/<cdu_id>/Pumps/<pump_id>"

        :param cdu_id: str
        :param pump_id: str
        :param body: dict
        :return: dict
        """
        mode = True if body["Mode"] == "Enabled" else False
        payload = self._build_pumps_post_payload(cdu_id, pump_id, mode)
        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json=payload, #{"mode": "manual", f"pump{pump_id}_switch": mode},
                timeout=5
            )
            
            return {"message": f"Pump{pump_id} Update Success"}, r.status_code
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.INTERNAL_ERROR,
                message=f"PATCH {CDU_BASE}/api/v1/cdu/status/op_mode FAIL: details={str(e)}"
            )

        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            # return {
            #     "error": "Forwarding to the CDU control service failed",
            #     "details": str(e)
            # }, 502  
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE,
                message=f"Forwarding to the CDU control service failed: {str(e)}"
            )
    

    
    
    
    
    ##
    # TODO: 將來如果oem的邏輯很多，再考慮引入builder pattern
    ##
    def _config_cdu_model(self, m: RfCduModel) -> RfCduModel:
        raise NotImplementedError
    # def _build_oem_for_PrimaryCoolantConnectorModel(self, m: PrimaryCoolantConnectorModel) -> dict:
    #     raise NotImplementedError
    def _build_pumps_patch_payload(self, cdu_id: str, pump_id: str, body: dict) -> dict:
        raise NotImplementedError
    def _build_pumps_post_payload(self, cdu_id: str, pump_id: str, mode: dict) -> dict:
        raise NotImplementedError
    def _build_filter(self, cdu_id: str, filter_id: str) -> dict:
        raise NotImplementedError
    def _build_leakdetectors_id(self, cdu_id: str, leak_detector_id: str) -> dict:
        raise NotImplementedError

class RfSidecarThermalEquipmentService(RfThermalEquipmentService):
    def fetch_CDUs_PrimaryCoolantConnectorsId(self, cdu_id: str, coolant_connector_id: str) -> dict:
        m = self.build_CoolantConnectorModel(cdu_id, coolant_connector_id, CoolantConnectorEnums.PRIMARY.value)
        m.Oem = self._build_oem_for_PrimaryCoolantConnectorModel(m)
        return m.to_dict()
    
    def fetch_CDUs_SecondaryCoolantConnectorsId(self, cdu_id: str, coolant_connector_id: str) -> dict:
        raise ProjError(HTTPStatus.NOT_FOUND)

    def _config_cdu_model(self, m: RfCduModel) -> RfCduModel:
        m.SecondaryCoolantConnectors = None
        # m.Coolant = {
        #     "CoolantType": "Water",
        #     "DensityKgPerCubicMeter": 1030, 
        #     "SpecificHeatkJoulesPerKgK": 3900,
        # }
        m.Coolant = RfCoolantModel(
            CoolantType=RfCoolantType.Water,
            DensityKgPerCubicMeter=1030,
            SpecificHeatkJoulesPerKgK=3900
        )
        return m

    def _build_oem_for_PrimaryCoolantConnectorModel(self, m: RfThermalEquipmentService.PrimaryCoolantConnectorModel) -> dict:
        """
        Build value of PrimaryCoolantConnectorModel.Oem
        """
        pump_swap_time = None
        try:
            pump_swap_time = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/control/pump_swap_time")
        except Exception:
            pump_swap_time = -1
        return {
            "Supermicro": {
                "PumpSwapTime": {
                    "@odata.type": "#supermicro.PumpSwapTime.v1_0_0.PumpSwapTime",
                    "SetPoint": pump_swap_time,
                    "Units": "Hours"
                }
            }
        }
    def _build_pumps_patch_payload(self, cdu_id: str, pump_id: str, body: dict) -> dict:
        payload = {
            "mode": body["SpeedControlPercent"].get("ControlMode"),
            "pump_speed": body["SpeedControlPercent"].get("SetPoint")
        }
        return payload    
    
    def _build_pumps_post_payload(self, cdu_id: str, pump_id: str, mode: bool) -> dict:
        payload = {
            "mode": "manual",
            f"pump{pump_id}_switch": mode
        }
        return payload
    
    def _build_filter(self, cdu_id: str, filter_id: str) -> dict:
        all_data = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/chassis/summary")
        thermal_equipment = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/thermal_equipment/summary")
        health_data = (all_data["pressure_filter_in"]["status"], all_data["pressure_filter_out"]["status"])
        ServiceHours = thermal_equipment.get("Filter_run_time", -1)
        return health_data, ServiceHours
    
    def _build_leakdetectors_id(self, cdu_id: str, leak_detector_id: str) -> dict:
        return None

class RfInrowcduThermalEquipmentService(RfThermalEquipmentService):
    def fetch_CDUs_PrimaryCoolantConnectorsId(self, cdu_id: str, coolant_connector_id: str) -> dict:
        m = self.build_CoolantConnectorModel(cdu_id, coolant_connector_id, CoolantConnectorEnums.PRIMARY.value)
        m.Oem = None
        return m.to_dict()
    
    def fetch_CDUs_SecondaryCoolantConnectorsId(self, cdu_id: str, coolant_connector_id: str) -> dict:
        m = self.build_CoolantConnectorModel(cdu_id, coolant_connector_id, CoolantConnectorEnums.SECONDARY.value)
        m.Oem = None
        return m.to_dict()

    def _config_cdu_model(self, m: RfCduModel) -> RfCduModel:
        cdu_id = m.Id        
        m.SecondaryCoolantConnectors = {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors"
        }
        # m.Coolant = {
        #     "CoolantType": "PropyleneGlycolAq",
        #     "AdditiveName": "Propylene Glycol",
        #     "AdditivePercent": 25,
        #     "DensityKgPerCubicMeter": 1030,
        #     "SpecificHeatkJoulesPerKgK": 3.4
        # }
        m.Coolant = RfCoolantModel(
            CoolantType=RfCoolantType.Water,
            AdditiveName="Propylene Glycol",
            AdditivePercent=25,
            DensityKgPerCubicMeter=1030,
            SpecificHeatkJoulesPerKgK=3.4
        )
        return m
    
    def _build_pumps_patch_payload(self, cdu_id: str, pump_id: str, body: dict) -> dict:
        setpoint = body["SpeedControlPercent"].get("SetPoint")
        payload = {
            "mode": body["SpeedControlPercent"].get("ControlMode"),
            f"pump{pump_id}_speed": setpoint,
        }
        return payload
    
    def _build_pumps_post_payload(self, cdu_id: str, pump_id: str, mode: bool) -> dict:
        if mode == False:
            setpoint = 0
        else:
            if pump_id == "1":
                setpoint = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")["pump2speed"]
                if setpoint == 0:
                    setpoint = hardware_info.get("Pumps", 0).get(pump_id, 0).get("AllowableMin", 50)
            elif pump_id == "2":
                setpoint = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")["pump1speed"]
                if setpoint == 0:
                    setpoint = hardware_info.get("Pumps", 0).get(pump_id, 0).get("AllowableMin", 50)                
        payload = {
            "mode": "manual",
            f"pump{pump_id}_speed": setpoint,
        }  
        return payload

    def _build_filter(self, cdu_id: str, filter_id: str) -> dict:
        all_data = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/chassis/summary")
        thermal_equipment = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/thermal_equipment/summary")
        health_data = (all_data["pressure_filter_in"]["status"], all_data[f"pressure_filter_{filter_id}_out"]["status"])
        ServiceHours = thermal_equipment.get(f"Filter_{filter_id}_run_time", -1)
        return health_data, ServiceHours
    
    def _build_leakdetectors_id(self, cdu_id: str, leak_detector_id: str) -> dict:
        leak_switch = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/setting")
        test = sensor_info.get("leak_detectors").get(leak_detector_id).get("fieldNameToFetchSensorValue")
        leak_switch_id = leak_switch.get(test, -1) # -1 讓他報錯
        return leak_switch_id

class RfThermalEquipmentServiceFactory:
    projname_serice_map = {
        ProjNames.SIDECAR.value: RfSidecarThermalEquipmentService,
        ProjNames.INROW_CDU.value: RfInrowcduThermalEquipmentService,
    }
    @classmethod
    def get_service(cls) -> RfThermalEquipmentService:
        proj_name = os.environ["PROJ_NAME"]
        if proj_name in cls.projname_serice_map:
            return cls.projname_serice_map[proj_name]()
        else:
            raise ProjError(code=HTTPStatus.BAD_REQUEST, message=f"Unknown project name: {proj_name}")