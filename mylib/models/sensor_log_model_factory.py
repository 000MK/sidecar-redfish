from pydantic import BaseModel, Field, ConfigDict, create_model
import yaml
import os
from typing import Type, Optional
from http import HTTPStatus
from mylib.common.proj_constant import ProjNames
from mylib.common.proj_error import ProjError
from mylib.models.sensor_log_model import (
    SensorLogBaseModel,
    SensorLogModel,
    SidecarSensorLogModel,
    InrowcduSensorLogModel,
)

        

"""
Usage:
    model_instance = SensorLogModelFactory.create_model(
        {"field1": 1.0, "field2": 2.0, "field3": 3.0}
    )
"""
class SensorLogModelFactory:
    registered_models = {
        # "SensorLogModel": SensorLogModel, # for proj-name=sidecar-redfish
        ProjNames.SIDECAR: SidecarSensorLogModel,
        ProjNames.INROW_CDU: InrowcduSensorLogModel,
    }

    @classmethod
    def get_model(cls, proj_name: str) -> Type[SensorLogModel]:
        """
        Return the model class based on the given model name
        """
        model_class = cls.registered_models.get(proj_name)
        if model_class is None:
            raise ProjError(HTTPStatus.NOT_FOUND, f"Unknown proj name: {proj_name}")
        return model_class
    
    @classmethod
    def create_model(cls, data: dict=None) -> SensorLogModel:
        """
        Create a model instance based on the given model name
        """
        proj_name = os.getenv("PROJ_NAME")

        if proj_name in cls.registered_models:
            model_class = cls.get_model(proj_name)
            if data is None:
                return model_class()
            else:
                return model_class(**data)
        else:
            raise ProjError(HTTPStatus.NOT_FOUND, f"PROJ_NAME, {proj_name},  not found in env!")


    
