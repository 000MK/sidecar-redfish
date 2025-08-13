from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask import abort
from http import HTTPStatus
import requests
import importlib
import os
from typing import Dict
from load_env import hardware_info, sensor_info
from mylib.services.rf_chassis_service import RfChassisService, RfChassistServiceFactory
from mylib.utils.load_api import load_raw_from_api 
from mylib.utils.load_api import CDU_BASE
from mylib.common.my_resource import MyResource
from mylib.utils.system_info import get_system_uuid
from mylib.common.proj_error import ProjRedfishError, ProjRedfishErrorCode
from mylib.common.proj_constant import ProjNames
from mylib.common.proj_error import ProjError
from mylib.utils.JsonUtil import JsonUtil
# from models.rf_chassis_model import RfChassisModel, RfStatusModel


Chassis_ns = Namespace('Chassis', description='Chassis Collection')
Chassis_ThermalSubsystem_Fans_ns = Namespace('Chassis.ThermalSubsystem.Fans', description='Chassis ThermalSubsystem')

Chassis_data = {
    "@odata.id": "/redfish/v1/Chassis",
    "@odata.type": "#ChassisCollection.ChassisCollection",
    "@odata.context": "/redfish/v1/$metadata#ChassisCollection.ChassisCollection",
    "Name": "Chassis Collection",
    "Members@odata.count": 1,
    "Members": [{"@odata.id": "/redfish/v1/Chassis/1"}],
    "Description": "A collection of all chassis resources",
    "Oem": {}
}


PowerSubsystem_data = {
    "@odata.id": "/redfish/v1/Chassis/1/PowerSubsystem",
    "@odata.type": "#PowerSubsystem.v1_1_3.PowerSubsystem",
    "@odata.context": "/redfish/v1/$metadata#PowerSubsystem.v1_1_3.PowerSubsystem",
    
    "Id": "PowerSubsystem",
    "Name": "Chassis Power Subsystem",
    "Description":   "Chassis Power Subsystem",
    
    "Status": {
        "State": "Enabled", 
        "Health": "OK"
    },
    
    # 整個子系統的額定最大功率
    # 一次工作一組 360w
    # 24v 240w 12v 120w
    "CapacityWatts": JsonUtil.get_nested_value(hardware_info, "PowerSubsystem.CapacityWatts"), # 360
    
    # 本次與下游元件協商分配與請求的功率 TBD
    "Allocation": {
        "AllocatedWatts": JsonUtil.get_nested_value(hardware_info, "PowerSubsystem.Allocation.AllocatedWatts"), # 80.0
        "RequestedWatts": JsonUtil.get_nested_value(hardware_info, "PowerSubsystem.Allocation.RequestedWatts") # 90.0
    },
    
    # 與各個電源模組的關聯
    "PowerSupplies": {
        "@odata.id": "/redfish/v1/Chassis/1/PowerSubsystem/PowerSupplies"
    },
    
    "Oem": {}
}

#================================================
# Chassis 驗證器
#================================================
class MyBaseChassis(MyResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chassis_count = 1
        self.power_supply_count = len(hardware_info.get("PowerSupplies", {}))
        self.fan_count = len(hardware_info.get("Fans", {}))
        self.control_count = len(hardware_info.get("Controls", {}) or {})
        self.sensor_count = len(hardware_info.get("id_readingInfo_map", {}))
    
    def _validate_request(self):
        try:
            chassis_id = request.view_args.get("chassis_id")
            power_supply_id = request.view_args.get("power_supply_id")
            fan_id = request.view_args.get("fan_id")
            control_id = request.view_args.get("control_id")
            sensor_id = request.view_args.get("sensor_id")
            if not self._is_valid_id(chassis_id, self.chassis_count):
                abort(HTTPStatus.NOT_FOUND, description=f"chassis_id, {chassis_id}, not found")
            
            if not self._is_valid_id(power_supply_id, self.power_supply_count):
                abort(HTTPStatus.NOT_FOUND, description=f"power_supply_id, {power_supply_id}, not found")
            
            if not self._is_valid_id(fan_id, self.fan_count):
                abort(HTTPStatus.NOT_FOUND, description=f"fan_id, {fan_id}, not found")
                
            if not self._hardware_validator(control_id, "Controls"):   
                abort(HTTPStatus.NOT_FOUND, description=f"control_id, {control_id}, not found") 
                
            if not self._sensor_validator(sensor_id, "id_readingInfo_map"):
                abort(HTTPStatus.NOT_FOUND, description=f"sensor_id, {sensor_id}, not found")
        except Exception as e:
            abort(HTTPStatus.NOT_FOUND, description=f"[Unexpected Error] {e}")
    
    def _is_valid_id(self, id: str, max_value: int):
        if id: # request有傳id進來才檢查
            if not id.isdigit():
                return False
            if not (0 < int(id) <= max_value):
                return False
        return True

    def _hardware_validator(self, hardware_id: str, hardware_name: str) -> bool:
        if hardware_id:
            if hardware_id not in hardware_info[hardware_name].keys():
                return False
        return True
    
    def _sensor_validator(self, sensor_id: str, sensor_name: str) -> bool:
        if sensor_id:
            if sensor_id not in sensor_info[sensor_name].keys():
                return False
        return True
#================================================
# 機箱資源（Chassis）
#================================================
@Chassis_ns.route("/Chassis")
class Chassis(Resource):
    # # @requires_auth
    def get(self):
        return Chassis_data


@Chassis_ns.route("/Chassis/<chassis_id>")
class Chassis1(MyBaseChassis):
    # # @requires_auth
    def get(self, chassis_id):
        return RfChassistServiceFactory.get_service().get_chassis_data(chassis_id)

#================================================
# 控制介面（Controls）
#================================================
ControlId_patch_model = Chassis_ns.model('controlidpatch', {
    'SetPoint': fields.Float(
        # required=True,
        description='control Id SetPoint',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'ControlMode': fields.String(
        # required=True,
        description='control Id ControlMode',
        default=True,   # 是否設定預設值
        example="Automatic",   # 讓 UI 顯示範例
        enum=['Automatic', 'Manual', 'Disabled']
    ),
})
# controls 資源
@Chassis_ns.route("/Chassis/<chassis_id>/Controls")
class Controls(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        
        # return Controls_data
        return RfChassistServiceFactory.get_service().get_control(chassis_id)
    
  
@Chassis_ns.route("/Chassis/<chassis_id>/Controls/<control_id>")
class ControlsById(MyBaseChassis): # GET PATCH
    # @requires_auth
    def get(self, chassis_id, control_id):
        return RfChassistServiceFactory.get_service().get_control_by_id(chassis_id, control_id)   
    
    @Chassis_ns.expect(ControlId_patch_model, validate=True)  
    def patch(self, chassis_id, control_id):
        body = request.get_json(force=True)
        return RfChassistServiceFactory.get_service().patch_control_by_id(chassis_id, control_id, body) 
    
#================================================
# 電源子系統（PowerSubsystem）
#================================================

@Chassis_ns.route("/Chassis/<chassis_id>/PowerSubsystem")
class PowerSubsystem(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        rep = PowerSubsystem_data
        status = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/components/chassis/summary")["power_total"]["status"]
        rep["Status"]["State"], rep["Status"]["Health"] = status["state"], status["health"]
        return rep


@Chassis_ns.route("/Chassis/<chassis_id>/PowerSubsystem/PowerSupplies")
class PowerSupplies(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        chassis_service = RfChassisService()
        rep = chassis_service.fetch_PowerSubsystem_PowerSupplies(chassis_id)
        return rep

@Chassis_ns.route("/Chassis/<chassis_id>/PowerSubsystem/PowerSupplies/<power_supply_id>")
class PowerSuppliesById(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id: str, power_supply_id: str):
        chassis_service = RfChassisService()
        # TBD
        rep = chassis_service.fetch_PowerSubsystem_PowerSupplies(chassis_id, power_supply_id)
        #  ['AC100To127V', 'AC100To240V', 'AC100To277V', 'AC120V', 'AC200To240V', 'AC200To277V', 'AC208V', 'AC230V', 'AC240V', 'AC240AndDC380V', 'AC277V', 'AC277AndDC380V', 'AC400V', 'AC480V', 'DC48V', 'DC240V', 'DC380V', 'DCNeg48V', 'DC16V', 'DC12V', 'DC9V', 'DC5V', 'DC3_3V', 'DC1_8V']
        rep["Metrics"] = {"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/PowerSupplies/{power_supply_id}/Metrics"}
        rep["Assembly"] = {"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/PowerSupplies/{power_supply_id}/Assembly"}
     
        return rep
    
@Chassis_ns.route("/Chassis/<chassis_id>/PowerSubsystem/PowerSupplies/<power_supply_id>/Assembly")
class Assembly(MyBaseChassis):    
    # @requires_auth
    def get(self, chassis_id: str, power_supply_id: int):
        Assembly_data = {
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/PowerSupplies/{power_supply_id}/Assembly",
            "@odata.type": "#Assembly.v1_5_1.Assembly",
            
            "Id": str(power_supply_id),
            "Name": "Assembly",
        }
        return Assembly_data
    
@Chassis_ns.route("/Chassis/<chassis_id>/PowerSubsystem/PowerSupplies/<string:power_supply_id>/Metrics")
class PowerSuppliesMetrics(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id, power_supply_id):
        power_Metrics_data = {
            "@odata.context": "/redfish/v1/$metadata#PowerSupplyMetrics.PowerSupplyMetrics",
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/PowerSupplies/{power_supply_id}/Metrics",
            "@odata.type": "#PowerSupplyMetrics.v1_1_2.PowerSupplyMetrics",
            
            "Id": f"PowerSupplyMetrics{power_supply_id}",
            "Name": "Chassis Power Supply Metrics",
            
            # "FrequencyHz":{"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors/FrequencyHz"},
            # "InputCurrentAmps":{"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors/InputCurrentAmps"},
            # "InputPowerWatts":{"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors/InputPowerWatts"},
            # "InputVoltage":{"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors/InputVoltage"},
            # "OutputPowerWatts":{"@odata.id": f"/redfish/v1/Chassis/{chassis_id}/Sensors/OutputPowerWatts"},
            "Status": {
                "State": "Enabled",
                "Health": "OK"
            },
            # 這裡最少要有一個 Reading 欄位
            # "ReadingWatts": 480.0
        }
        return power_Metrics_data   
#================================================
# 感測器（Sensors）
#================================================
@Chassis_ns.route("/Chassis/<chassis_id>/Sensors")
class Sensors(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        chassis_service = RfChassisService()
        return chassis_service.fetch_sensors_collection(chassis_id)


@Chassis_ns.route("/Chassis/<chassis_id>/Sensors/<sensor_id>")
class FetchSensorsById(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id: str, sensor_id: str) -> Dict:
        """
        :param sensor_id: str, e.g. PrimaryFlowLitersPerMinute, CPUFan1, CPUFan2, ...
        :return: dict

        @see https://www.dmtf.org/sites/default/files/standards/documents/DSP2064_1.1.0.pdf Section 5.6.6, 5.13
        """
        chassis_service = RfChassisService()
        rep = chassis_service.fetch_sensors_by_name(chassis_id, sensor_id)

        return jsonify(rep)
#================================================
# 散熱子系統（ThermalSubsystem）
#================================================
# OperationMode patch model設置
FanSwitch_patch = Chassis_ns.model('FanSwitchpatch', {
    'SetPoint': fields.Integer(
        required=True,
        description='Fan_Speed',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'ControlMode': fields.String(
        required=True,
        description='Switch_Mode',
        default=True,   # 是否設定預設值
        example="Manual",   # 讓 UI 顯示範例
        enum=['Automatic', 'Manual', 'Disabled']
    ),
})

Fan_model = Chassis_ns.model('FanModel', {
    'SpeedControlPercent': fields.Nested(FanSwitch_patch, description='Fan settings')
})

@Chassis_ns.route("/Chassis/<chassis_id>/ThermalSubsystem")
class ThermalSubsystem(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        return RfChassistServiceFactory().get_service().fetch_thermal_subsystem(chassis_id)
        # return ThermalSubsystem_data


@Chassis_ThermalSubsystem_Fans_ns.route("/Chassis/<chassis_id>/ThermalSubsystem/Fans")
class ThermalSubsystem_Fans(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        # super().get()
        ThermalSubsystem_Fans_data = RfChassistServiceFactory().get_service()
        return ThermalSubsystem_Fans_data.get_thermal_subsystem_fans_count(chassis_id)


@Chassis_ThermalSubsystem_Fans_ns.route("/Chassis/<chassis_id>/ThermalSubsystem/Fans/<string:fan_id>")
class ThermalSubsystem_Fans_by_id(MyBaseChassis):
    # @requires_auth
    def get(self, fan_id, chassis_id):
        ThermalSubsystem_Fans_by_id = RfChassistServiceFactory().get_service()
        rep = ThermalSubsystem_Fans_by_id.get_thermal_subsystem_fans_data(chassis_id, fan_id)

        return  rep, 200
    
    @Chassis_ns.expect(Fan_model, validate=True)
    def patch(self, chassis_id, fan_id):
        body = request.get_json(force=True)
        
        return RfChassisService().patch_thermal_subsystem_fans_data(chassis_id, fan_id, body)
    
@Chassis_ns.route("/Chassis/<chassis_id>/ThermalSubsystem/ThermalMetrics")
class ThermalMetrics(MyBaseChassis):
    # @requires_auth
    def get(self, chassis_id):
        ThermalMetrics_data = {
            "@odata.context": "/redfish/v1/$metadata#ThermalMetrics.ThermalMetrics",
            "@odata.id": f"/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/ThermalMetrics",
            "@odata.type": "#ThermalMetrics.v1_3_2.ThermalMetrics",
            
            "Id": "ThermalMetrics",
            "Name": "Chassis Thermal Metrics",
            
            "TemperatureSummaryCelsius": {
                "Ambient": {
                    "DataSourceUri": "/redfish/v1/Chassis/1/Sensors/TemperatureCelsius",
                },
                "Exhaust": {
                    "DataSourceUri": "/redfish/v1/Chassis/1/Sensors/PrimarySupplyTemperatureCelsius",
                },
                "Intake": {
                    "DataSourceUri": "/redfish/v1/Chassis/1/Sensors/PrimaryReturnTemperatureCelsius",
                },
            }
        }
        return ThermalMetrics_data    
# ================================================================
# Valve
# ================================================================   
# @Chassis_ns.route("/Chassis/<chassis_id>/Controls/Valve")
# class ThermalEquipmentCdus1Valve(MyBaseChassis):
#     # # @requires_auth
#     @Chassis_ns.doc("thermal_equipment_cdus_1_valve")
#     def get(self, cdu_id):
#         thermal_equipment_service = RfChassistServiceFactory.get_service()
#         return thermal_equipment_service.fetch_CDUs_Valve(cdu_id)
    
#     def patch(self, cdu_id):
#         thermal_equipment_service = RfChassistServiceFactory.get_service()
#         return thermal_equipment_service.patch_CDUs_Valve(cdu_id)
#================================================
# Supermicro OEM Operation 資源
#================================================
# 動態 import
proj = os.environ["PROJ_NAME"]
module_name = f"etc.software.{proj}.name_space_mode_ldefnitions"
class_name  = "Operation_patch_model"  
mod = importlib.import_module(module_name)
OperationPatchModel = getattr(mod, class_name)
payload = OperationPatchModel().Operation_patch
Operation_patch = Chassis_ns.model('OperationInrow', payload)

if proj == "sidecar-redfish":
    @Chassis_ns.route("/Chassis/<chassis_id>/Controls/Oem/Supermicro/Operation")
    class Operation(MyBaseChassis):
        # @requires_auth
        def get(self, chassis_id):
            return RfChassisService().get_Oem_Spuermicro_Operation(chassis_id)

        @Chassis_ns.expect(Operation_patch, validate=True)
        def patch(self, chassis_id):
            body = request.get_json(force=True)
            
            return RfChassisService().patch_Oem_Spuermicro_Operation(chassis_id, body)