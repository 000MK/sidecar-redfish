from mylib.utils.rf_error import *
import copy
import json
import os
from load_env import registry_info

registry_base_info = registry_info["Base"]

class RfRegistries():

    @classmethod
    def fetch_registries(cls):
        """
        Get registries
        """
        registries = copy.deepcopy(cls.registries_default)
        return registries
    
    @classmethod
    def fetch_registry_base(cls):
        """
        Get Base registry
        """
        register_base = copy.deepcopy(cls.register_base_default)
        return register_base
    
    @classmethod
    def fetch_registry_base_v1_21_0(cls):
        return copy.deepcopy(registry_base_info)

    registries_default = {
        "@odata.context": "/redfish/v1/$metadata#MessageRegistryFileCollection.MessageRegistryFileCollection",
        "@odata.id": "/redfish/v1/Registries",
        "@odata.type": "#MessageRegistryFileCollection.MessageRegistryFileCollection",
        "Name": "Message Registry File Collection",
        "Description": "A collection of Message Registries available in the service.",
        "Members@odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Registries/Base"
            }
        ]
    }
    
    register_base_default = {
        "@odata.context": "/redfish/v1/$metadata#MessageRegistryFile.MessageRegistryFile",
        "@odata.id": "/redfish/v1/Registries/Base",
        "@odata.type": "#MessageRegistryFile.v1_21_0.MessageRegistryFile",
        "Id": "Base",
        "Name": "Base Message Registry",
        "Description": "This registry defines the common base messages for Redfish.",
        "Language": "en",
        "Registry": "Base",
        "OwningEntity": "DMTF",
        "Location": [
            {
                "Uri": "/redfish/v1/Registries/Base/Base.v1_21_0"
            }
        ]
    }