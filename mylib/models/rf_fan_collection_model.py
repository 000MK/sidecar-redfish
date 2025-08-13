
from typing import Optional, List, Dict, Any
from pydantic import (
    BaseModel,
    Field, 
    computed_field,
    model_validator,
    #validator, # deprecated
    field_validator,
)
from mylib.models.rf_base_model import RfResourceCollectionBaseModel


class RfFanCollectionModel(RfResourceCollectionBaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/FanCollection.json#/definitions/FanCollection
    """
    # 所有欄位都同 RfResourceCollectionBaseModel 
    def __init__(self, chassis_id: str, **kwargs):
        super().__init__(**kwargs)
        self.odata_id = f"/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/Fans"
        self.odata_type = "#FanCollection.FanCollection"
        self.odata_context = "/redfish/v1/$metadata#Fans.FanCollection"
        self.Name = "Fans Collection"

