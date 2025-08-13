
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
from mylib.models.rf_resource_model import RfResourceModel

class RfCoolantConnectorCollectionModel(RfResourceCollectionBaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/CoolantConnectorCollection
    """
    def __init__(self, cdu_id: str, **kwargs):
        super().__init__(**kwargs)
        self.odata_type = "#CoolantConnectorCollection.CoolantConnectorCollection"
    #     self.Name = "Primary (supply side) Cooling Loop Connection Collection"
    #     self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors"
        
    #     member_cnt = int(os.environ.get('REDFISH_PRIMARYCOOLANTCONNECTOR_COLLECTION_CNT', 0))
    #     for sn in range(1, member_cnt + 1):
    #         self.Members.append({"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors/{sn}"})
    #     self.Members_odata_count = member_cnt
    # pass


class RfCoolantConnectorModel(RfResourceModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/CoolantConnector.v1_2_0.json
    @note 34 items
    """
    
    Coolant: Optional[Dict[str, Any]] = Field(default=None)
    CoolantConnectorType: Optional[str] = Field(default=None)
    DeltaTemperatureCelsius: Optional[Dict[str, Any]] = Field(default=None)
    DeltaPressureControlkPa: Optional[Dict[str, Any]] = Field(default=None)
    DeltaPressurekPa: Optional[Dict[str, Any]] = Field(default=None)
    Description: Optional[str] = Field(default=None)
    FlowLitersPerMinute: Optional[Dict[str, Any]] = Field(default=None) 
    HeatRemovedkW: Optional[Dict[str, Any]] = Field(default=None)
    RatedFlowLitersPerMinute: Optional[int] = Field(default=None)
    ReturnPressurekPa: Optional[Dict[str, Any]] = Field(default=None)
    ReturnTemperatureCelsius: Optional[Dict[str, Any]] = Field(default=None)
    SupplyPressurekPa: Optional[Dict[str, Any]] = Field(default=None)
    SupplyTemperatureCelsius: Optional[Dict[str, Any]] = Field(default=None)
    SupplyTemperatureControlCelsius: Optional[Dict[str, Any]] = Field(default=None)
    Status: Optional[RfStatusModel] = Field(default=None) 
    Oem: Optional[Dict[str, Any]] = Field(default=None)
    
    model_config = ConfigDict(
        extra='allow',
    )

    def __init__(self, cdu_id: str, coolant_connector_id: str, **kwargs):
        super().__init__(**kwargs)
        ##
        # Just example!
        # Please Use Factory Pattern to disinguish from PrimaryCoolantConnectorModel and SecondaryCoolantConnectorModel
        ##
        # self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors/{coolant_connector_id}"
        self.odata_type = "#CoolantConnector.v1_1_0.CoolantConnector"
        self.Odata_context = "/redfish/v1/$metadata#CoolantConnector.v1_1_0.CoolantConnector"
        
        self.Id = coolant_connector_id
        # self.Name = "Mains Input from Chiller"
        # self.Description = "Primary input from facility chiller (no valve control)"