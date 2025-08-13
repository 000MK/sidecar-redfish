import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pydantic import (
    BaseModel,
    ConfigDict,
    Field, 
    computed_field,
    model_validator,
    #validator, # deprecated
    field_validator,
)
from typing_extensions import Self
from enum import Enum
from mylib.models.rf_base_model import RfResourceBaseModel, RfResourceCollectionBaseModel
from mylib.models.rf_status_model import RfStatusModel
from mylib.models.rf_assembly_model import RfAssemblyModel
from mylib.models.rf_filter_collection_model import RfFilterCollectionModel
from mylib.models.rf_sensor_model import RfSensorExcerpt
from mylib.models.rf_resource_model import RfLocationModel, RfOemModel
from mylib.models.rf_physical_context_model import RfPhysicalContext
from mylib.models.rf_sensor_model import RfSensorPumpExcerpt
from mylib.models.rf_control_model import RfControlSingleLoopExcerptModel
from mylib.models.rf_sensor_model import RfSensorPowerExcerpt, RfSensorFanExcerpt
from load_env import hardware_info

        

class RfChassisModel(RfResourceBaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/Chassis.json#/definitions/Chassis
    @see https://redfish.dmtf.org/schemas/v1/Chassis.v1_26_0.json#/definitions/Chassis
    @note 65 items
    """
    
    # 標準硬體資訊
    Description: Optional[str] = Field(default="", description="Chassis Description")
    ChassisType: Optional[str] = Field(default="", description="Type of Chassis (e.g., Rack, Sidecar)")
    Manufacturer: Optional[str] = Field(default="", description="Manufacturer")
    Model: Optional[str] = Field(default="", description="Model Name")
    SerialNumber: Optional[str] = Field(default="", description="Serial Number")
    PartNumber: Optional[str] = Field(default="", description="Part Number")
    UUID: Optional[str] = Field(default="", description="System UUID")
    AssetTag: Optional[str] = Field(default="", description="Asset Tag")
    SKU: Optional[str] = Field(default="", description="SKU Number")
    Version: Optional[str] = Field(default="", description="Firmware or software version")

    # 狀態與指示燈
    PowerState: Optional[str] = Field(default="On", description="Power state")
    LocationIndicatorActive: Optional[bool] = Field(default=True, description="LED indicator")
    Status: Optional[RfStatusModel] = Field(default=None, description="Chassis health and state")

    # 子資源連結
    PowerSubsystem: Optional[Dict[str, Any]] = Field(default={}, description="Power Subsystem")
    ThermalSubsystem: Optional[Dict[str, Any]] = Field(default={}, description="Thermal Subsystem")
    EnvironmentMetrics: Optional[Dict[str, Any]] = Field(default={}, description="Environment Metrics")
    Sensors: Optional[Dict[str, Any]] = Field(default={}, description="Sensor Collection")
    Controls: Optional[Dict[str, Any]] = Field(default={}, description="Control Collection")

    # Links / Actions / OEM
    Links: Optional[Dict[str, Any]] = Field(default={}, description="Related resource links")
    Actions: Optional[Dict[str, Any]] = Field(default={}, description="Available actions")
    Redfish_WriteableProperties: Optional[List[str]] = Field(default=["LocationIndicatorActive"], alias="@Redfish.WriteableProperties")
    Oem: Optional[Dict[str, Any]] = Field(default={}, description="OEM extensions")


    model_config = ConfigDict(
        extra="allow",
    )

    def __init__(self, chassis_id: str , **kwargs):
        super().__init__(**kwargs)
        self.Id = chassis_id
        self.odata_id = f"/redfish/v1/Chassis/{chassis_id}"
        self.odata_type = "#Chassis.v1_26_0.Chassis"
        self.odata_context = "/redfish/v1/$metadata#Chassis.v1_26_0.Chassis"
        self.Name = f"Catfish System Chassis {chassis_id}"
        self.Description = f"Main rack-mount chassis #{chassis_id} for Catfish System"
    
    # Odata_context: Optional[str] = Field(default=None, alias="@odata.context")
    # Odata_etag: Optional[str] = Field(default=None, alias="@odata.etag")
    # # "@odata.id": {1 item},
    # # "@odata.type": {1 item},
    # "Actions": {3 items},
    # "Assembly": {5 items},
    # "AssetTag": {4 items},
    # "Certificates": {5 items},
    # "ChassisType": {4 items},
    # "Controls": {5 items},
    # "DepthMm": {7 items},
    # "Description": {2 items},
    # "Doors": {4 items},
    # "Drives": {4 items},
    # "ElectricalSourceManagerURIs": {7 items},
    # "ElectricalSourceNames": {6 items},
    # "EnvironmentMetrics": {5 items},
    # "EnvironmentalClass": {5 items},
    # "FabricAdapters": {5 items},
    # "HeatingCoolingEquipmentNames": {6 items},
    # "HeatingCoolingManagerURIs": {7 items},
    # "HeightMm": {7 items},
    # "HotPluggable": {5 items},
    # "Id": {2 items},
    # "IndicatorLED": {6 items},
    # "LeakDetectors": {5 items},
    # "Links": {3 items},
    # "Location": {4 items},
    # "LocationIndicatorActive": {5 items},
    # "LogServices": {4 items},
    # "Manufacturer": {4 items},
    # "MaxPowerWatts": {6 items},
    # "Measurements": {7 items},
    # "MediaControllers": {7 items},
    # "Memory": {5 items},
    # "MemoryDomains": {5 items},
    # "MinPowerWatts": {6 items},
    # "Model": {4 items},
    # "Name": {2 items},
    # "NetworkAdapters": {5 items},
    # "Oem": {3 items},
    # "PCIeDevices": {5 items},
    # "PCIeSlots": {7 items},
    # "PartNumber": {4 items},
    # "PhysicalSecurity": {4 items},
    # "Power": {6 items},
    # "PowerState": {5 items},
    # "PowerSubsystem": {5 items},
    # "PoweredByParent": {5 items},
    # "Processors": {5 items},
    # "Replaceable": {5 items},
    # "SKU": {4 items},
    # "Sensors": {5 items},
    # "SerialNumber": {4 items},
    # "SparePartNumber": {5 items},
    # "Status": {3 items},
    # "Thermal": {6 items},
    # "ThermalDirection": {5 items},
    # "ThermalManagedByParent": {5 items},
    # "ThermalSubsystem": {5 items},
    # "TrustedComponents": {5 items},
    # "UUID": {5 items},
    # "Version": {5 items},
    # "WeightKg": {7 items},
    # "WidthMm": {7 items}
    # pass
    

                
