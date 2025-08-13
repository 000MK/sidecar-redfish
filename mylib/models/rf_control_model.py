from typing import Optional
from pydantic import (
    BaseModel,
    Field,
    validator, # deprecated
    field_validator,
)
from enum import Enum
from mylib.models.rf_base_model import RfResourceBaseModel

        
class RfControlLoop(BaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/Control.v1_6_0.json#/definitions/ControlLoop
    """
    CoefficientUpdateTime: Optional[str] = Field(default=None, description="The date and time that the control loop coefficients were changed.")
    Differential: Optional[float] = Field(default=None, description="The differential coefficient.")
    Integral: Optional[float] = Field(default=None, description="The integral coefficient.")
    Proportional: Optional[float] = Field(default=None, description="The proportional coefficient.")

class RfControlMode(str, Enum):
    """
    @see https://redfish.dmtf.org/schemas/v1/Control.v1_6_0.json#/definitions/ControlMode
    """
    Automatic = "Automatic"
    Override = "Override"
    Manual = "Manual"
    Disabled = "Disabled"

class RfControlSingleLoopExcerptModel(BaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/Control.v1_6_0.json#/definitions/ControlSingleLoopExcerpt
    """
    DataSourceUri: Optional[str] = Field(default=None)
    AllowableMax: Optional[float] = Field(default=None)
    AllowableMin: Optional[float] = Field(default=None)
    ControlLoop: Optional[RfControlLoop] = Field(default=None, description="The control loop details.")
    ControlMode: Optional[RfControlMode] = Field(default=None)
    Reading: Optional[float] = Field(default=None)
    ReadingUnits: Optional[str] = Field(default=None)
    SetPoint: Optional[float] = Field(default=None, description="The desired set point of the control.")
    SpeedRPM: Optional[float] = Field(default=None, json_schema_extra={"units": "{rev}/min"})
                
class RfControlId(RfResourceBaseModel):
    Odata_contrxt: Optional[str] = Field(default=None)
    SetPoint: Optional[float] = Field(default=None, description="The desired set point of the control.")
    ControlMode: Optional[RfControlMode] = Field(default=None)
    
    
    def __init__(self, chassis_id: str, control_id: str, **kwargs):
        super().__init__(**kwargs)
        self.odata_id = f"/redfish/v1/Chassis/{chassis_id}/Controls/{control_id}"
        self.odata_type = "#Control.v1_6_0.Control"    
        
        self.Id = control_id
        self.Name = control_id