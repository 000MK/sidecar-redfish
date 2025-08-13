from flask_restx import Namespace, Resource, fields

Operation_patch_Inrow = {
    'ControlMode': fields.String(
        required=True,
        description='Switch_Mode',
        default=True,   # 是否設定預設值
        example="Manual",   # 讓 UI 顯示範例
        enum=['Automatic', 'Manual', 'Disabled']
    ),
    'TargetTemperature': fields.Float(
        # required=True,
        description='Target_Temperature',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'TargetPressure': fields.Float(
        # required=True,
        description='Target_Pressure',
        default=True,   # 是否設定預設值
        example=10,   # 讓 UI 顯示範例
    ),
    'Pump1Speed': fields.Float(
        # required=True,
        description='Pump1_Speed',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'Pump2Speed': fields.Float(
        # required=True,
        description='Pump2_Speed',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'PV1': fields.Float(
        # required=True,
        description='PV1',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
}

class Operation_patch_model:
    def __init__(self):
        self.Operation_patch = Operation_patch_Inrow   



class ThermalEquipment_model:
    def __init__(self, setting, oem_model=None):
        # PrimaryCoolantConnectors_model = {
        #     'SupplyTemperatureControlCelsius': fields.Nested(setting, description='PrimaryCoolantConnectors settings'),
        #     'DeltaPressureControlkPa': fields.Nested(setting, description='PrimaryCoolantConnectors settings'),
        #     'Oem': fields.Nested(oem_model, required=False, description='OEM specific parameters')
        # }
        SecondaryCoolantConnectors_model = {
            'SupplyTemperatureControlCelsius': fields.Nested(setting, description='SecondaryCoolantConnectors settings'),
            'DeltaPressureControlkPa': fields.Nested(setting, description='SecondaryCoolantConnectors settings'),
        }
        # self.PrimaryCoolantConnectors_patch_model = PrimaryCoolantConnectors_model
        self.SecondaryCoolantConnectors_patch_model = SecondaryCoolantConnectors_model