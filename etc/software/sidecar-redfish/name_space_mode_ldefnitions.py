from flask_restx import Namespace, Resource, fields
Operation_patch_Sidecar =  {
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
    'PumpSwapTime': fields.Integer(
        # required=True,
        description='Pump_Swap_Time',
        default=True,   # 是否設定預設值
        example=100,   # 讓 UI 顯示範例
    ),
    'FanSetPoint': fields.Float(
        # required=True,
        description='Fan_Set_Point',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'PumpSetPoint': fields.Float(
        # required=True,
        description='Pump_Set_Point',
        default=True,   # 是否設定預設值
        example=50,   # 讓 UI 顯示範例
    ),
    'Pump1Switch': fields.Boolean(
        # required=True,
        description='Pump1_Switch',
        default=True,   # 是否設定預設值
        example=True,   # 讓 UI 顯示範例
    ),
    'Pump2Switch': fields.Boolean(
        # required=True,
        description='Pump2_Switch',
        default=True,   # 是否設定預設值
        example=True,   # 讓 UI 顯示範例
    ),
    'Pump3Switch': fields.Boolean(
        # required=True,
        description='Pump3_Switch',
        default=True,   # 是否設定預設值
        example=True,   # 讓 UI 顯示範例
    )

} 

class Operation_patch_model:
    def __init__(self):
        self.Operation_patch = Operation_patch_Sidecar
        

class ThermalEquipment_model:
    def __init__(self, setting, oem_model=None):
        PrimaryCoolantConnectors_model = {
            'SupplyTemperatureControlCelsius': fields.Nested(setting, description='PrimaryCoolantConnectors settings'),
            'DeltaPressureControlkPa': fields.Nested(setting, description='PrimaryCoolantConnectors settings'),
            'Oem': fields.Nested(oem_model, required=False, description='OEM specific parameters')
        }
        SecondaryCoolantConnectors_model = {
            'SupplyTemperatureControlCelsius': fields.Nested(setting, description='SecondaryCoolantConnectors settings'),
            'DeltaPressureControlkPa': fields.Nested(setting, description='SecondaryCoolantConnectors settings'),
        }
        self.PrimaryCoolantConnectors_patch_model = PrimaryCoolantConnectors_model
        # self.SecondaryCoolantConnectors_patch_model = SecondaryCoolantConnectors_model