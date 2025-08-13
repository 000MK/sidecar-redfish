'''
這是Redfish的chassis service
'''
import os, re, json
import time
import requests
from typing import Optional
from mylib.models.rf_sensor_model import (
    RfSensorCollectionModel, 
    RfSensorModel, 
)
from mylib.models.rf_status_model import RfStatusModel, RfStatusHealth, RfStatusState
from mylib.services.base_service import BaseService
from mylib.models.rf_power_supply_model import RfPowerSupplyCollectionModel, RfPowerSupplyModel
from mylib.models.rf_cdu_model import RfCduModel, RfCduCollectionModel
from mylib.models.rf_control_collection_model import RfControlCollectionExcerptModel
from mylib.models.rf_control_model import RfControlSingleLoopExcerptModel, RfControlId
from mylib.models.rf_fan_collection_model import RfFanCollectionModel
from mylib.models.rf_fan_model import RfFanModel
from mylib.models.rf_resource_model import RfLocationModel, RfOemModel
from mylib.models.rf_thermal_subsystem_model import RfThermalSubsystemModel
from cachetools import LRUCache, cached
from typing import Dict, Any
from load_env import hardware_info, sensor_info
from mylib.utils.load_api import load_raw_from_api, CDU_BASE
from mylib.utils.controlUtil import ControlMode_change
from mylib.common.proj_error import ProjRedfishError, ProjRedfishErrorCode
from mylib.utils.system_info import get_uptime
from mylib.utils.system_info import get_system_uuid
from mylib.common.proj_constant import ProjConstant, ProjNames
from mylib.common.proj_error import ProjError
from http import HTTPStatus
from mylib.models.rf_chassis_model import RfChassisModel

class RfChassisService(BaseService):

    def get_fans_cnt(self):
        return len(hardware_info.get("Fans", ""))
    
    # SENSOR_IDS = {
    #     "PrimaryFlowLitersPerMinute",
    #     "PrimaryHeatRemovedkW",
    #     "PrimarySupplyTemperatureCelsius",
    #     "PrimaryReturnTemperatureCelsius",
    #     "PrimaryDeltaTemperatureCelsius",
    #     "PrimarySupplyPressurekPa",
    #     "PrimaryReturnPressurekPa",
    #     "PrimaryDeltaPressurekPa",
    #     "TemperatureCelsius",
    #     "DewPointCelsius",
    #     "HumidityPercent",
    #     "WaterPH",
    #     "Conductivity",
    #     "Turbidity",
    #     "PowerConsume",
    # }

    def get_chassis_data(self, chassis_id: str) -> dict:
        """
        對應 "/redfish/v1/Chassis/1"

        :param chassis_id: str
        :return: dict
        """
        m = RfChassisModel(
            chassis_id=chassis_id,
            **hardware_info["CDU"]
        )
        
        version = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/display/version")
        version_data = version.get("fw_info", {})
        m.Model = version_data.get("Model")
        m.SerialNumber = version_data.get("SN")
        m.PartNumber = version_data.get("PartNumber")
        m.Version = version.get("version", {}).get("Redfish_Server")
        m.AssetTag = version_data.get("SN")
        m.UUID = get_system_uuid()
        m.SKU = "130-D0150000A0-T01"
        # 子資源連結
        m.PowerSubsystem = {
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/PowerSubsystem"
        }
        m.ThermalSubsystem = {
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem"
        }
        m.EnvironmentMetrics = {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/EnvironmentMetrics"
        }
        m.Sensors = {
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors"
        }
        m.Controls = {
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Controls"
        }
        
        # Links 與 OEM 擴充
        m.Status = RfStatusModel(State="Enabled", Health="OK")
        m.Links = {
            "ManagedBy": [{"@odata.id": "/redfish/v1/Managers/CDU"}],
            "CoolingUnits": [{"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}"}]
        }
        # m.Oem = {
        #     "supermicro": {
        #         "@odata.type": "#Oem.Chassis.v1_26_0.Chassis",
        #         "LeakDetection": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/LeakDetection"},
        #         "Pumps": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/Pumps"},
        #         "PrimaryCoolantConnectors": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/PrimaryCoolantConnectors"},
        #         "Main MC": {"State": "ON"}
        #     }
        m = self._build_oem_of_RfChassisModel(m)
        # }
        
        return m.to_dict()

    def fetch_thermal_subsystem(self, chassis_id: str) -> dict:
        """
        對應 "/redfish/v1/Chassis/{CHASSIS_ID}/ThermalSubsystem"
        ex: "/redfish/v1/Chassis/1/ThermalSubsystem"
        """
        m = RfThermalSubsystemModel(chassis_id = chassis_id)
        m.ThermalMetrics = {
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/ThermalMetrics"
        }
        m.Fans = self._build_ThermalSubsystem(m)
        m.Status = RfStatusModel(State="Enabled", Health="OK")
        return m.to_dict()


    def fetch_sensors_collection(self, chassis_id: str) -> dict:
        """
        對應 "/redfish/v1/Chassis/{CHASSIS_ID}/Sensors"
        ex: "/redfish/v1/Chassis/1/Sensors
        """
        sensor_ids = list(sensor_info.get("id_readingInfo_map").keys())
        SENSOR_IDS = {*sensor_ids}
        # 動態調整風扇數量
        fan_cnt = hardware_info.get("FanCount") #self.get_fans_cnt() 
        for i in range(fan_cnt):
            SENSOR_IDS.add(f"Fan{i+1}")
            
        sensor_collection_model = RfSensorCollectionModel()
        sensor_collection_model.odata_id = sensor_collection_model.build_odata_id(chassis_id)

        for sensor_id in SENSOR_IDS:
            sensor_collection_model.Members.append({"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors/{sensor_id}"})
        sensor_collection_model.Members = sorted(sensor_collection_model.Members, key=lambda x: x["@odata.id"])
        sensor_collection_model.Members_odata_count = len(sensor_collection_model.Members)
        return sensor_collection_model.to_dict()

    def fetch_sensors_by_name(self, chassis_id: str, sensor_name: str) -> dict:
        """
        對應 "/redfish/v1/Chassis/{CHASSIS_ID}/Sensors/{SENSOR_NAME}"
        ex: "/redfish/v1/Chassis/1/Sensors/PrimaryFlowLitersPerMinute"

        :param chassis_id: str
        :param sensor_name: str, ex: PrimaryFlowLitersPerMinute|PrimaryHeatRemovedkW|...
        :return: dict
        """
        id_readingInfo_spare = sensor_info.get("id_readingInfo_spare", {})
        
        reading_info = self._load_reading_info_by_sensor_id(sensor_name)
        m = RfSensorModel(
            chassis_id=chassis_id,
            Id = sensor_name,
            Name = self._camel_to_words(sensor_name),
            Reading=reading_info["Reading"],
            ReadingUnits = reading_info["ReadingUnits"],
            Status = RfStatusModel(Health=reading_info["Status"].get("Health") or reading_info["Status"].get("health"), State=reading_info["Status"].get("State") or reading_info["Status"].get("state"))
        )

        if m.Status.Health == "Critical":
            if sensor_name in id_readingInfo_spare:
                all_sensor_reading = self._read_components_chassis_summary_from_cache()
                spare_field = id_readingInfo_spare[sensor_name]["fieldNameToFetchSensorValue"]

                m.Reading = 0
                m.Oem = {
                    "Supermicro": {
                        "@odata.type": "#Supermicro.Sensor.v1_0_0.Sensor",
                        "ReadingSpare": all_sensor_reading[spare_field + "_spare"]["reading"],
                        "StatusSpare": all_sensor_reading[spare_field + "_spare"]["status"],
                    }
                }
        
        resp_json = m.to_dict()
        return resp_json
    
    def fetch_PowerSubsystem_PowerSupplies(self, chassis_id: str, power_supply_id: str = None):
        """
        對應 /Chassis/1/PowerSubsystem/PowerSupplies (if `power_supply_id` is None)
        對應 /Chassis/1/PowerSubsystem/PowerSupplies/{power_supply_id}
        :param power_supply_id: str, ex: 1. 
        :return: dict
        :note 
            (1) 目前有四個PowerSupplies：24V * 2台，12V * 2台，RestAPI不會對應電源與Id的關係，由redfish自己mapping
        """
        ret_json = None

        summary_info = self._read_components_chassis_summary_from_cache() # why no chassis_id?

        if power_supply_id is None:
            m = RfPowerSupplyCollectionModel(chassis_id=chassis_id)
        else:
            id_name_dict = self.__read_power_supply_id_name_dict()
            if power_supply_id not in id_name_dict.keys():
                raise ProjRedfishError(
                    ProjRedfishErrorCode.INTERNAL_ERROR, 
                    f"PowerSupply {power_supply_id} not found"
                )
            power_supply_name = id_name_dict[power_supply_id]["RestName"]
            
            m = RfPowerSupplyModel(
                chassis_id=chassis_id,
                Id = power_supply_id,
                **hardware_info.get("PowerSupplies", {}).get(power_supply_id)
            )
            m.Status = RfStatusModel.from_dict(summary_info.get(power_supply_name, {}).get("status", {"State": "Enabled", "Health": "OK"}))

        return m.to_dict()
    
    @cached(cache=LRUCache(maxsize=3))
    def __read_power_supply_id_name_dict(self) -> Dict[str, Any]:
        """
        Generate mapping of (PowerSupplyId, restAPI name)
        (key, value) = (Redfish PowerSupplyId, Name respond from RestAPI)
        """
        json_formatted_str = hardware_info.get("PowerSupplies", "{}")
        # PowerSupplyId_Name_dict = json.loads(json_formatted_str)
        return json_formatted_str

    def _load_reading_info_by_sensor_id(self, sensor_id: str) -> str:
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
        fan_cnt = hardware_info.get("FanCount") 
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
            reading_info["Reading"] = 0.0  
        return reading_info
    
    # 取得 thermal_subsystem 風扇數量
    def get_thermal_subsystem_fans_count(self, chassis_id: str):
        m = RfFanCollectionModel(chassis_id=chassis_id)
        m.Members_odata_count = hardware_info.get("FanCount") #self.get_fans_cnt()
        for i in range(m.Members_odata_count):
            m.Members.append({
                "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/Fans/{i+1}"
            })
        return m.to_dict()

    # 取得 thermal_subsystem 風扇資訊
    def get_thermal_subsystem_fans_data(self, chassis_id: str, fan_id: str):
        m = RfFanModel(chassis_id=chassis_id, fan_id=fan_id)
        sensor_value_json = self._read_components_chassis_summary_from_cache()

        # 位置服務標籤
        Location = {
            "PartLocation": {
                "ServiceLabel": hardware_info["Fans"][fan_id]["Location"]["PartLocation"]["ServiceLabel"]
            }
        }
        m.Location = RfLocationModel(**Location)

        m.Status = RfStatusModel().from_dict(sensor_value_json["fan" + str(fan_id)]["status"])
        # m.Status.State = sensor_value_json["fan" + str(fan_id)]["status"]["state"]
        # m.Status.Health = sensor_value_json["fan" + str(fan_id)]["status"]["health"]
        fan_mc_id = 1 if int(fan_id) <= 3 else 2
        m.Oem = {
            "Supermicro": {
                "@odata.type": "#Supermicro.FanMC",
                f"Fan Gorup{fan_mc_id} MC": {
                    "fan MC":load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/mc")[f"fan_mc{fan_mc_id}"]
                }
            }
        }

        opmode_data = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")
        m.SpeedControlPercent = {
            "SetPoint": load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/Oem")["FanSetPoint"],
            "ControlMode": ControlMode_change(opmode_data["mode"]),
            "AllowableMax": hardware_info.get("Fans").get(fan_id).get("AllowableMax"),
            "AllowableMin": hardware_info.get("Fans").get(fan_id).get("AllowableMin")
        }
        resp = m.to_dict() 
        
        # service validator 不會過
        # 速度感測器連結
        SpeedPercent = {
            "DataSourceUri": f"/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/Sensors/Fan{fan_id}",
            "Reading":  sensor_value_json["fan" + str(fan_id)]["reading"],
            "SpeedRPM": sensor_value_json["fan" + str(fan_id)]["reading"] * 16000 / 100,
        }
        resp["SpeedPercent"] = SpeedPercent
        
        return resp
    
    def patch_thermal_subsystem_fans_data(self, chassis_id: str, fan_id: str, body: dict):
        
        # 這裡是 patch 的內容
        ControlMode = body["SpeedControlPercent"]["ControlMode"]
        SetPoint = body["SpeedControlPercent"]["SetPoint"]
        ControlMode = ControlMode_change(ControlMode)

        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json={
                    "mode": ControlMode, 
                    "fan_speed": SetPoint,
                    "fan1_switch": True,
                    "fan2_switch": True,
                    "fan3_switch": True,
                    "fan4_switch": True,
                    "fan5_switch": True,
                    "fan6_switch": True,
                    "fan7_switch": True,
                    "fan8_switch": True
                },
                timeout=3
            )
            r.raise_for_status()
           
            
            time.sleep(2)  # 延遲問題要解決 setpoint(目前為暫解)
            return self.get_thermal_subsystem_fans_data(chassis_id, fan_id), 200
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                ProjRedfishErrorCode.INTERNAL_ERROR, 
                f"PATCH {CDU_BASE}/api/v1/cdu/status/op_mode FAIL: {str(e)}"
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
            
    
    def get_Oem_Spuermicro_Operation(self, chassis_id: str):
        rep = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/Oem")
        rep["ControlMode"] = ControlMode_change(rep["ControlMode"])
        rep["@odata.id"] = f"/redfish/v1/Chassis/{chassis_id}/Controls/Oem/Supermicro/Operation"
        rep["@odata.type"] = "#Supermicro.Control"
        rep["Id"] = "Operation"
        rep["Name"] = "Supermicro Control Operation"
        if rep.get("PumpSwapTime"):
            rep["PumpSwapTime"] = round(rep["PumpSwapTime"], 2)
        
        return rep, 200
    
    def patch_Oem_Spuermicro_Operation(self, chassis_id: str, body: dict):
        ControlMode = body.get("ControlMode")
        # TargetTemperature = body.get("TargetTemperature")
        # TargetPressure = body.get("TargetPressure")
        # PumpSwapTime = body.get("PumpSwapTime")
        # FanSetPoint = body.get("FanSetPoint")
        # PumpSetPoint = body.get("PumpSetPoint")
        # Pump1Switch = body.get("Pump1Switch")
        # Pump2Switch = body.get("Pump2Switch")
        # Pump3Switch = body.get("Pump3Switch")

        # data = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/Oem")
        ControlMode = ControlMode_change(ControlMode)
        body["ControlMode"] = ControlMode
        
        svc = RfChassistServiceFactory.get_service()
        payload = svc._build_oem_payload_for_supermicro(chassis_id, body)

        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json=payload,
                timeout=3
            )
            r.raise_for_status()      
            code = r.status_code
            time.sleep(2)
            return self.get_Oem_Spuermicro_Operation(chassis_id)

        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                ProjRedfishErrorCode.INTERNAL_ERROR, 
                f"/api/v1/cdu/status/op_mode FAIL: {str(r.text)}"
            )
        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            raise ProjRedfishError(
                ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE, 
                f"Forwarding to the CDU control service failed: {str(e)}"
            )
            
        
        
    def get_control(self, chassis_id: str):
        m = RfControlCollectionExcerptModel(chassis_id = chassis_id)
        
        data = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/Oem")
        m.Oem = self._get_controls_oem_supermicro(chassis_id, data)
        
        return m.to_dict()
    
    def get_control_by_id(self, chassis_id: str, control_id: str) -> dict:
        """
        對應 GET "/redfish/v1/ThermalEquipment/CDUs/<cdu_id>/Valves"

        :param cdu_id: str
        :return: dict
        """
        op_mode = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")
        m = RfControlId(chassis_id=chassis_id, control_id=control_id)
        m.SetPoint = op_mode.get(hardware_info.get("Controls",{}).get(control_id).get("RestAPIName"))
        m.ControlMode = ControlMode_change(op_mode["mode"])
        return m.to_dict()
    
    def patch_control_by_id(self, chassis_id: str, control_id: str, body) -> dict:
        """
        對應 PATCH "/redfish/v1/ThermalEquipment/CDUs/<cdu_id>/Valves"

        :param cdu_id: str
        :return: dict
        """
        SetPoint = body.get("SetPoint")
        RestAPIName = hardware_info.get("Controls",{}).get(control_id).get("RestAPIName")
        ControlMode = body.get("ControlMode","Manual")
        mode = ControlMode_change(ControlMode)
        # 轉發到內部控制 API
        try:
            r = requests.patch(
                f"{CDU_BASE}/api/v1/cdu/status/op_mode",
                json={
                    "mode": mode,
                    RestAPIName: SetPoint
                },
                timeout=3
            )
            r.raise_for_status()      
            code = r.status_code
            time.sleep(2)
            return self.get_control_by_id(chassis_id, control_id)

        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                ProjRedfishErrorCode.INTERNAL_ERROR, 
                f"/api/v1/cdu/status/op_mode FAIL: {str(r.text)}"
            )
        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            raise ProjRedfishError(
                ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE, 
                f"Forwarding to the CDU control service failed: {str(e)}"
            )
    
    def _build_oem_of_RfChassisModel(self, m: RfChassisModel) -> RfChassisModel:
        raise NotImplementedError
    
    def _build_oem_payload_for_supermicro(self, chassis_id: str, data: dict) -> dict:
        # print(f"實際呼叫類別：{self.__class__.__name__}")
        raise NotImplementedError
    def _get_controls_oem_supermicro(self, chassis_id: str, data: dict) -> dict:
        # print(f"實際呼叫類別：{self.__class__.__name__}")
        raise NotImplementedError
    
    def _build_ThermalSubsystem(self, m:RfThermalSubsystemModel) -> dict:
        # print(f"實際呼叫類別：{self.__class__.__name__}")
        raise NotImplementedError

class RfSidecarChassisService(RfChassisService):
    def _build_oem_of_RfChassisModel(self, m: RfChassisModel) -> RfChassisModel:
        chassis_id = m.Id
        m.Oem = {
            "supermicro": {
                "@odata.type": "#Oem.Chassis.v1_26_0.Chassis",
                "LeakDetection": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/LeakDetection"},
                "Pumps": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/Pumps"},
                "PrimaryCoolantConnectors": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/PrimaryCoolantConnectors"},
                "Main MC": {"State": "ON"}
            }
        }
        return m
    
    def _build_oem_payload_for_supermicro(self, chassis_id: str, data: dict) -> dict:
        payload = {
            "mode":            data.get("ControlMode"),
            "temp_set":        data.get("TargetTemperature"),
            "pressure_set":    data.get("TargetPressure"),
            "pump_swap_time":  data.get("PumpSwapTime"),
            "pump_speed":      data.get("PumpSetPoint"),
            "pump1_switch":    data.get("Pump1Switch"),
            "pump2_switch":    data.get("Pump2Switch"),
            "pump3_switch":    data.get("Pump3Switch"),
            "fan_speed":       data.get("FanSetPoint"),
            **{f"fan{i}_switch": True for i in range(1, 9)},
        }
        return payload

    def _get_controls_oem_supermicro(self, chassis_id: str, data: dict) -> dict:
        payload = {
            ProjConstant.OEM_VENDOR: {
                "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Controls/Oem/Supermicro/Operation",
                "@odata.type": "#Supermicro.Control",
                "ControlMode":ControlMode_change(data["ControlMode"]), # Disable / Automatic / Manual
                "TargetTemperature": data["TargetTemperature"],
                "TargetPressure": data["TargetPressure"],
                "PumpSwapTime": round(data["PumpSwapTime"], 2),
                "FanSetPoint": data["FanSetPoint"],
                "PumpSetPoint": data["PumpSetPoint"],
                "Pump1Switch": data["Pump1Switch"],
                "Pump2Switch": data["Pump2Switch"],
                "Pump3Switch": data["Pump3Switch"],
            }
        }
        return payload
    def _build_ThermalSubsystem(self, m:RfThermalSubsystemModel) -> dict:
        return {"@odata.id": "/redfish/v1/Chassis/1/ThermalSubsystem/Fans"}
    
class RfInrowcduChassisService(RfChassisService):
    def _build_oem_of_RfChassisModel(self, m: RfChassisModel) -> RfChassisModel:
        chassis_id = m.Id
        m.Oem = {
            ProjConstant.OEM_VENDOR: {
                "@odata.type": "#Oem.Chassis.v1_26_0.Chassis",
                "LeakDetection": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/LeakDetection"},
                "Pumps": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/Pumps"},
                "PrimaryCoolantConnectors": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/PrimaryCoolantConnectors"},
                "SecondaryCoolantConnectors": {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{chassis_id}/SecondaryCoolantConnectors"},
                # "Main MC": {"State": "ON"}
            }
        }
        return m

    def _build_oem_payload_for_supermicro(self, chassis_id: str, data: dict) -> dict:
        payload = {
            "mode": data.get("ControlMode"), 
            "temp_set": data.get("TargetTemperature"),
            "pressure_set": data.get("TargetPressure"),
            "pump1_speed": data.get("Pump1Speed"),
            "pump2_speed": data.get("Pump2Speed"),
            "PV1": data.get("PV1"),
        }
        return payload

    def _get_controls_oem_supermicro(self, chassis_id: str, data: dict) -> dict:
        payload = {
            ProjConstant.OEM_VENDOR: {
                "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Controls/Oem/Supermicro/Operation",
                "@odata.type": "#Supermicro.Control",
                "ControlMode":ControlMode_change(data["ControlMode"]), # Disable / Automatic / Manual
                "TargetTemperature": data["TargetTemperature"],
                "TargetPressure": data["TargetPressure"],
                "Pump1Speed": data["Pump1Speed"],
                "Pump2Speed": data["Pump2Speed"],
                "PV1": data["PV1"],
                "EV1": data["EV1"],
                "EV2": data["EV2"],
                "EV3": data["EV3"],
                "EV4": data["EV4"],
            }
        }
        return payload
    
    def _build_ThermalSubsystem(self, m:RfThermalSubsystemModel) -> dict:
        return None

class RfChassistServiceFactory:
    projname_serice_map = {
        ProjNames.SIDECAR.value: RfSidecarChassisService,
        ProjNames.INROW_CDU.value: RfInrowcduChassisService,
    }
    @classmethod
    def get_service(cls) -> RfChassisService:
        proj_name = os.environ["PROJ_NAME"]
        if proj_name in cls.projname_serice_map:
            return cls.projname_serice_map[proj_name]()
        else:
            raise ProjError(code=HTTPStatus.BAD_REQUEST, message=f"Unknown project name: {proj_name}")