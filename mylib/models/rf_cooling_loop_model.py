
import os
from dataclasses import dataclass
from enum import Enum
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


class RfCoolantType(str, Enum):
    """
    @see https://redfish.dmtf.org/schemas/v1/CoolingLoop.v1_0_3.json#/definitions/CoolantType
    """
    Water = "Water"
    Hydrocarbon = "Hydrocarbon"
    Fluorocarbon = "Fluorocarbon"
    Dielectric = "Dielectric"

class RfCoolantModel(BaseModel):
    """
    @see https://redfish.dmtf.org/schemas/v1/CoolingLoop.v1_0_3.json#/definitions/Coolant
    """
    AdditiveName: Optional[str] = Field(default=None, description="This property shall contain the name of the additive contained in the coolant.")
    AdditivePercent: Optional[float] = Field(default=None, description="The percent additives contained in the coolant.", json_schema_extra={"units": "%"})
    CoolantType: Optional[RfCoolantType] = Field(default=None, description="The type of coolant.")
    DensityKgPerCubicMeter: Optional[float] = Field(default=None, description="The density (kg/m^3) of the coolant.", json_schema_extra={"units": "kg/m3"})
    RatedServiceHours: Optional[float] = Field(default=None, description="The rated hours of service life for this coolant.")
    ServiceHours: Optional[float] = Field(default=None, description="The hours of service this coolant has provided.")
    ServicedDate: Optional[str] = Field(default=None, description="The date the coolant was last serviced.")
    SpecificHeatkJoulesPerKgK: Optional[float] = Field(default=None, description="The specific heat capacity (kJ/(kg*K)) of the coolant.", json_schema_extra={"units": "kJ/kg/K"})

    