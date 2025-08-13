import os
import importlib
from flask import request, abort
from flask_restx import Namespace, Resource, fields
from mylib.models.rf_environment_metrics_model import RfEnvironmentMetricsModel
from mylib.services.rf_ThermalEquipment_service import RfThermalEquipmentServiceFactory
from mylib.utils.load_api import load_raw_from_api 
from mylib.utils.load_api import CDU_BASE
from mylib.utils.controlUtil import GetControlMode
from mylib.utils.controlUtil import ControlMode_change
import requests
from http import HTTPStatus
from mylib.common.my_resource import MyResource
from mylib.common.proj_error import ProjRedfishError, ProjRedfishErrorCode
from load_env import hardware_info

ThermalEquipment_ns = Namespace('', description='ThermalEquipment Collection')

ThermalEquipment_data= {
    "@odata.id": "/redfish/v1/ThermalEquipment",
    "@odata.type": "#ThermalEquipment.v1_1_2.ThermalEquipment",
    "@odata.context": "/redfish/v1/$metadata#ThermalEquipmentCollection.ThermalEquipmentCollection",
    
    "Name": "Thermal Equipment",
    "Id": "ThermalEquipment",
    "Description": "List all thermal management equipment",
    
    "CDUs": {
        "@odata.id": "/redfish/v1/ThermalEquipment/CDUs"   
    },
}


# reservoirs = {
#     "@odata.id": "/redfish/v1/ThermalEquipment/CDUs/1/Reservoirs",
#     "@odata.type": "#ReservoirCollection.ReservoirCollection",
#     "@odata.context": "/redfish/v1/$metadata#ReservoirCollection.ReservoirCollection",
    
#     "Name": "Reservoir Collection",
#     "Description": "Reservoirs Collection",
#     "Members@odata.count": 1,
#     "Members": [
#         {
#             "@odata.id": "/redfish/v1/ThermalEquipment/CDUs/1/Reservoirs/1"
#         },
#     ],
#     "Oem":{}
# }

# reservoirs_1 = {
#     "@odata.id": "/redfish/v1/ThermalEquipment/CDUs/1/Reservoirs/1",
#     "@odata.type": "#Reservoir.v1_0_0.Reservoir",
#     "@odata.context": "/redfish/v1/$metadata#Reservoir.v1_0_0.Reservoir",
    
#     "Id": "1",
#     "Name": "Liquid Level",
#     "Description": "Primary reserve reservoir for CDU 1",
#     # 容量資訊
#     "ReservoirType": "Reserve",
#     "CapacityLiters": -1, # 最大容量 未有此功能填-1
#     "FluidLevelStatus": "OK",
#     # "FluidLevelPercent": { # 考慮要不要
#     #     "DataSourceUri": "/redfish/v1/Chassis/1/Sensors/ReservoirFluidLevelPercent",
#     #     "Reading": 82.5
#     # },
    
#     # 設備資訊
#     "Manufacturer": "Supermicro",
#     "Model": "ReservoirModelX",
#     "PartNumber": "RES-100",
#     "SparePartNumber": "SPN-100",
#     "PhysicalContext": "LiquidInlet",
#     # 狀態
#     "Status": {
#         "State": "Enabled",
#         "Health": "OK"
#     },
    
#     # 實體位置
#     "Location": {
#         "PartLocation": {
#             "ServiceLabel": "Reservoir 1",
#             "LocationType": "Bay"
#         }
#     },
#     "Oem": {}
# }

# ================================================================
# payload model設置
# ================================================================
# primarycoolantconnectors patch設置
setting = ThermalEquipment_ns.model('setting', {
    'SetPoint': fields.Float(
        # required=True,
        description='point setting',
        default=50,
    ),
    'ControlMode': fields.String(
        required=True,
        description='Switch_Mode',
        default=True,   # 是否設定預設值
        example="Automatic",   # 讓 UI 顯示範例
        enum=['Automatic', 'Manual', 'Disabled']
    ),
})
pumpswattime = ThermalEquipment_ns.model('pumpswattime', {
    "PumpSwapTime": fields.Integer(
        # required=True,
        description='pump swap time setting',
        default=50,
    ),
})
oem_model = ThermalEquipment_ns.model('PrimaryCoolantConnectorsOem', {
    'Supermicro': fields.Nested(pumpswattime, description='Supermicro OEM settings')
})
# PrimaryCoolantConnectors_model = ThermalEquipment_ns.model('PrimaryCoolantConnectors', {
#     'SupplyTemperatureControlCelsius': fields.Nested(setting, description='PrimaryCoolantConnectors settings'),
#     'DeltaPressureControlkPa': fields.Nested(setting, description='PrimaryCoolantConnectors settings'),
#     'Oem': fields.Nested(oem_model, required=False, description='OEM specific parameters')
# })

# 動態 import
proj = os.environ["PROJ_NAME"]
module_name = f"etc.software.{proj}.name_space_mode_ldefnitions"
class_name  = "ThermalEquipment_model"  
mod = importlib.import_module(module_name)
ThermalEquipmentModel = getattr(mod, class_name, {})
PrimaryCoolantConnectors_model = ThermalEquipment_ns.model('PrimaryCoolantConnectors_model', getattr(ThermalEquipmentModel(setting, oem_model), "PrimaryCoolantConnectors_patch_model", {}))
SecondaryCoolantConnectors_model = ThermalEquipment_ns.model('SecondaryCoolantConnectors_model', getattr(ThermalEquipmentModel(setting, oem_model), "SecondaryCoolantConnectors_patch_model", {}))
 
# pump patch設置
Pump_model = ThermalEquipment_ns.model('Pump', {
    'SpeedControlPercent': fields.Nested(setting, description='Pump settings'),
})

# ================================================================
# 驗證器
# ================================================================
class MyBaseThermalEquipment(MyResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cdu_count = int(os.getenv("REDFISH_CDUS_COLLECTION_CNT", 1))
        self.primary_coolant_connector_count = int(os.getenv("REDFISH_PRIMARY_COOLANT_CONNECTOR_COUNT", 1))
        self.secondary_coolant_connector_count = int(os.getenv("REDFISH_SECONDARY_COOLANT_CONNECTOR_COUNT", 1))
        self.leak_detector_count = len(hardware_info.get("leak_detectors", {}))
    
    def _validate_request(self):
        try:
            cdu_id = request.view_args.get("cdu_id")
            connector_id = request.view_args.get("connector_id")
            leak_detector_id = request.view_args.get("leak_detector_id")
            pumps_id = request.view_args.get("pump_id")

            if not self._is_valid_id(cdu_id, self.cdu_count):
                abort(HTTPStatus.NOT_FOUND, description=f"cdu_id, {cdu_id}, not found")
            
            if not self._is_valid_id(connector_id, self.primary_coolant_connector_count):
                abort(HTTPStatus.NOT_FOUND, description=f"connector_id, {connector_id}, not found")
                
            if not self._is_valid_id(connector_id, self.secondary_coolant_connector_count):
                abort(HTTPStatus.NOT_FOUND, description=f"connector_id, {connector_id}, not found")    
            
            if not self._hardware_validator(leak_detector_id, "leak_detectors"):
                abort(HTTPStatus.NOT_FOUND, description=f"leak_detector_id, {leak_detector_id}, not found")
            
            if not self._hardware_validator(pumps_id, "Pumps"):
                abort(HTTPStatus.NOT_FOUND, description=f"pumps_id, {pumps_id}, not found")
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


# ================================================================
# ThermalEquipment
# ================================================================
@ThermalEquipment_ns.route("/ThermalEquipment")
class ThermalEquipment(Resource):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment")
    def get(self):
        """get thermal equipment"""
        return ThermalEquipment_data
            
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs")
class ThermalEquipmentCdus(Resource):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus")
    def get(self):
        # return CDUs_data
        return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs()
    
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>")
class ThermalEquipmentCdus1(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus")
    def get(self, cdu_id: str):
        # return CDUs_data_1
        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs(cdu_id)
        return rep
    
# ================================================================
# PrimaryCoolantConnectors
# ================================================================    
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/PrimaryCoolantConnectors")
class PrimaryCoolantConnectors(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("primary_coolant_connectors")
    def get(self, cdu_id: str):
        return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_PrimaryCoolantConnectors(cdu_id)

methods = hardware_info.get("PrimaryCoolantConnectors").get("methods")
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/PrimaryCoolantConnectors/<connector_id>", methods=methods)
class PrimaryCoolantConnectors1(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("primary_coolant_connectors_1")
    def get(self, cdu_id: str, connector_id: str):
        return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_PrimaryCoolantConnectorsId(cdu_id, connector_id)
    
    @ThermalEquipment_ns.expect(PrimaryCoolantConnectors_model, validate=True)
    def patch(self, cdu_id: str, connector_id: str):
        body = request.get_json(force=True)
        return RfThermalEquipmentServiceFactory.get_service().patch_CDUs_PrimaryCoolantConnectorsId(cdu_id, connector_id, body)
    
# ================================================================
# SecondaryCoolantConnectors
# ================================================================    
if hardware_info.get("SecondaryCoolantConnectors"):
    @ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/SecondaryCoolantConnectors")
    class SecondaryCoolantConnectors(MyBaseThermalEquipment):
        # # @requires_auth
        @ThermalEquipment_ns.doc("secondary_coolant_connectors")
        def get(self, cdu_id: str):
            return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_SecondaryCoolantConnectors(cdu_id)
            
    @ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/SecondaryCoolantConnectors/<connector_id>")
    class SecondaryCoolantConnectorsId(MyBaseThermalEquipment):
        # # @requires_auth
        @ThermalEquipment_ns.doc("secondary_coolant_connectors_1")
        def get(self, cdu_id: str, connector_id: str):
            return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_SecondaryCoolantConnectorsId(cdu_id, connector_id)
            
        @ThermalEquipment_ns.expect(SecondaryCoolantConnectors_model, validate=True)
        def patch(self, cdu_id: str, connector_id: str):
            body = request.get_json(force=True)
            return RfThermalEquipmentServiceFactory.get_service().patch_CDUs_SecondaryCoolantConnectorsId(cdu_id, connector_id, body)    

# ================================================================
# Pumps
# ================================================================      

@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<string:cdu_id>/Pumps")
class ThermalEquipmentCdus1Pumps(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_pumps")
    def get(self, cdu_id):    
        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_Pumps(cdu_id)
        return rep
    
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<string:cdu_id>/Pumps/<string:pump_id>")
class ThermalEquipmentCdus1PumpsPump(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_pumps_pump")
    def get(self, cdu_id, pump_id):
        # 驗證 cdu_id 和 pump_id
        # self._validate_request()

        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_Pumps_Pump_get(cdu_id, pump_id)
        return rep
        
    # # @requires_auth
    @ThermalEquipment_ns.expect(Pump_model, validate=True)
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_pumps_pump")
    def patch(self, cdu_id, pump_id):
        # 驗證 cdu_id 和 pump_id
        # self._validate_request()
        
        body = request.get_json(force=True)
        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_Pumps_Pump_patch(cdu_id, pump_id, body)
        return rep
    
# ================================================================
# Filters
# ================================================================       
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/Filters")
class ThermalEquipmentCdus1Filters(Resource):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_filters")
    def get(self, cdu_id):
        return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_Filters(cdu_id)
    
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/Filters/<filter_id>")
class ThermalEquipmentCdus1Filters1(Resource):
    # # @requires_auth
    '''
    p3, p4其中一個broken他就broken
    warning, alert抓p4
    '''
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_filters_1")
    def get(self, cdu_id, filter_id):
        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_Filters_id(cdu_id, filter_id)
        return rep

# ================================================================
# EnvironmentMetrics
# ================================================================      
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/EnvironmentMetrics")
class ThermalEquipmentCdus1EnvironmentMetrics(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_environment_metrics")
    def get(self, cdu_id):
        thermal_equipment_service = RfThermalEquipmentServiceFactory.get_service()
        return thermal_equipment_service.fetch_CDUs_EnvironmentMetrics(cdu_id)

# ================================================================
# Reservoirs
# ================================================================      
# @ThermalEquipment_ns.route("/ThermalEquipment/CDUs/1/Reservoirs")
# class ThermalEquipmentCdus1Reservoirs(Resource):
#     # # @requires_auth
#     @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_reservoirs")
#     def get(self):
        
#         return reservoirs
    
    
# @ThermalEquipment_ns.route("/ThermalEquipment/CDUs/1/Reservoirs/1")
# class ThermalEquipmentCdus1Reservoirs1(Resource):
#     # # @requires_auth
#     @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_reservoirs_1")
#     def get(self):
        
#         return reservoirs_1

# ================================================================
# LeakDetection
# ================================================================   
@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/LeakDetection")
class LeakDetection(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_LeakDetection")
    def get(self, cdu_id):
        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_LeakDetection(cdu_id)
        
        # return LeakDetection_data    
        return rep

@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/LeakDetection/LeakDetectors")
class LeakDetectionLeakDetectors(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_LeakDetection_LeakDetectors")
    def get(self, cdu_id):
        rf_ThermalEquipment_service = RfThermalEquipmentServiceFactory.get_service()
        resp_json = rf_ThermalEquipment_service.fetch_CDUs_LeakDetection_LeakDetectors(cdu_id)
        return resp_json

@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<cdu_id>/LeakDetection/LeakDetectors/<string:leak_detector_id>")
class LeakDetectionLeakDetectors1(MyBaseThermalEquipment):
    # # @requires_auth
    @ThermalEquipment_ns.doc("thermal_equipment_cdus_1_LeakDetection_LeakDetectors_1")
    def get(self, cdu_id, leak_detector_id):
        # 驗證 cdu_id 和 leak_detector_id
        # if leak_detector_id not in hardware_info["leak_detectors"].keys():
        #     abort(HTTPStatus.NOT_FOUND, description=f"leak_detector_id, {leak_detector_id}, not found")
            
        rep = RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_LeakDetection_LeakDetectors_id(cdu_id, leak_detector_id)
        return rep

# ================================================================
# Actions
# ================================================================ 
Mode_common = ThermalEquipment_ns.model('CoolingUnitPatch', {
    'Mode': fields.String(
        required=True,
        description='Automatic Switch',
        default=True,
        example="Enabled",
        enum = ['Enabled', 'Disabled']
    ),
})

@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<string:cdu_id>/Actions/CoolingUnit.SetMode")
class CoolingUnitSetMode(Resource):
    # # @requires_auth
    @ThermalEquipment_ns.expect(Mode_common, validate=True)
    def post(self, cdu_id):
        data = request.get_json(force=True)
        return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_SetMode(cdu_id, data)


@ThermalEquipment_ns.route("/ThermalEquipment/CDUs/<string:cdu_id>/Pumps/<string:pump_id>/Actions/Pump.SetMode")
class PumpSetMode(Resource):
    # # @requires_auth
    @ThermalEquipment_ns.expect(Mode_common, validate=True)
    def post(self, cdu_id, pump_id):
        if pump_id not in hardware_info["Pumps"].keys():
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.GENERAL_ERROR,
                message=f"pump_id {pump_id} not found"
            )
        data = request.get_json(force=True)
        return RfThermalEquipmentServiceFactory.get_service().fetch_CDUs_Pumps_SetMode(cdu_id, pump_id, data)
