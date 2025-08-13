
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
from load_env import hardware_info


class RfFilterCollectionModel(RfResourceCollectionBaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/FilterCollection.json#/definitions/FilterCollection
    """
    # 所有欄位都同 RfResourceCollectionBaseModel 
    def __init__(self, cdu_id: str, **kwargs):
        super().__init__(**kwargs)
        self.odata_id = f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters"
        self.odata_type = "#FilterCollection.FilterCollection"
        
        self.Name = "Filters Collection"
        self.Members_odata_count = len(hardware_info["Filters"])
        self.Members = [
            {
                "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters/{filter_id}"
            } for filter_id in hardware_info["Filters"]
        ]


