from enum import Enum
import os

class ProjNames(str, Enum):
    SIDECAR = "sidecar-redfish"
    INROW_CDU = "inrow-cdu"

class ProjConstant:
    PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    OEM_VENDOR = "Supermicro"

    @classmethod
    def set_proj_root(cls, proj_root: str):
        cls.PROJ_ROOT = proj_root

    @classmethod
    def build_env_filepath(cls, proj_name: str, env_filename: str) -> str:
        return os.path.join(cls.PROJ_ROOT, "etc", "env", proj_name, env_filename)

    @classmethod
    def build_hardware_info_filepath(cls, proj_name: str) -> str:
        return os.path.join(cls.PROJ_ROOT, "etc", "hardware", proj_name, "hardware_info.yaml")

    @classmethod
    def build_software_info_filepath(cls, proj_name: str) -> str:
        return os.path.join(cls.PROJ_ROOT, "etc", "software", proj_name, "software_info.yaml")

    @classmethod
    def build_sensor_info_filepath(cls, proj_name: str) -> str:
        return os.path.join(cls.PROJ_ROOT, "etc", "sensor", proj_name, "sensor_info.yaml")