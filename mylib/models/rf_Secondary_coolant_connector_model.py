
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

from mylib.models.rf_base_model import RfResourceBaseModel, RfResourceCollectionBaseModel
from mylib.models.rf_status_model import RfStatusModel

# class RfSecondaryCoolantConnectorCollectionModel(RfResourceCollectionBaseModel):
#     def __init__(self, cdu_id: str, **kwargs):
#         super().__init__(**kwargs)
#         self.odata_type = "#CoolantConnectorCollection.CoolantConnectorCollection"
#         self.Name = "Secondary (supply side) Cooling Loop Connection Collection"
#         self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors"
        
#         member_cnt = int(os.environ.get('REDFISH_SECONDARYCOOLANTCONNECTOR_COLLECTION_CNT', 0))
#         for sn in range(1, member_cnt + 1):
#             self.Members.append({"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors/{sn}"})
#         self.Members_odata_count = member_cnt


# class RfSecondaryCoolantConnectorModel(RfResourceBaseModel):
#     Odata_context: Optional[str] = Field(default=None, alias="@odata.context")
#     Description: Optional[str] = Field(default="Primary input from facility chiller")
    
#     RatedFlowLitersPerMinute: Optional[int] = Field(default=None)
    
#     Coolant: Optional[Dict[str, Any]] = Field(default=None)
#     CoolantConnectorType: Optional[str] = Field(default=None)
#     FlowLitersPerMinute: Optional[Dict[str, Any]] = Field(default=None) 
#     HeatRemovedkW: Optional[Dict[str, Any]] = Field(default=None)
#     SupplyTemperatureCelsius: Optional[Dict[str, Any]] = Field(default=None)
#     ReturnTemperatureCelsius: Optional[Dict[str, Any]] = Field(default=None)
#     DeltaTemperatureCelsius: Optional[Dict[str, Any]] = Field(default=None)
#     SupplyPressurekPa: Optional[Dict[str, Any]] = Field(default=None)
#     ReturnPressurekPa: Optional[Dict[str, Any]] = Field(default=None)
#     DeltaPressurekPa: Optional[Dict[str, Any]] = Field(default=None)
#     SupplyTemperatureControlCelsius: Optional[Dict[str, Any]] = Field(default=None)
#     DeltaPressureControlkPa: Optional[Dict[str, Any]] = Field(default=None)
    
#     Status: Optional[RfStatusModel]   = Field(default=None) 
#     Oem: Optional[Dict[str, Any]] = None

#     model_config = ConfigDict(
#         extra='allow',
#     )

#     def __init__(self, cdu_id: str, secondray_coolant_connector_id: str, **kwargs):
#         super().__init__(**kwargs)
#         self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors/{secondray_coolant_connector_id}"
#         self.odata_type = "#CoolantConnector.v1_1_0.CoolantConnector"
#         self.Odata_context = "/redfish/v1/$metadata#CoolantConnector.v1_1_0.CoolantConnector"
        
#         self.Id = secondray_coolant_connector_id
#         self.Name = f"SecondaryCoolantConnector{secondray_coolant_connector_id}"
#         self.Description = "Secondary input from facility chiller"