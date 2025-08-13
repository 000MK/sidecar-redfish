'''
Run:
    python app.py --env=dev --proj-name=sidecar-redfish
'''
from argparse import ArgumentParser
import sys, os, platform
from dotenv import load_dotenv
import yaml,json
from mylib.common.proj_constant import ProjConstant

class AppPathInitializer:
    def __init__(self, params={}):
        self.platform = platform.system()
        
    def initialize(self):
        db_root = os.getenv("PROJ_SQLITE_ROOT", "")
        db_filename_suffix = "-test" if os.getenv("IS_TESTING_MODE") == "True" else ""
        db_filename = f"mydb{db_filename_suffix}.sqlite"
        db_filepath = os.path.join(db_root, db_filename)

        if self.platform in ['Linux', 'Darwin']:
            # Maybe it's better to move to installation process.
            if db_root != "" and not os.path.exists(db_root):
                try:
                    os.makedirs(db_root)
                    print(f"Created folder: {db_root}")
                except Exception as e:
                    # Handle exception for `flask shell`
                    print(f"Error creating folder: {e}")

        elif self.platform == 'Windows':
            db_filepath = db_filename
        
        return {
            "db_filename": db_filename,
            "db_filepath": db_filepath
        }
        


arg_parser = ArgumentParser()
arg_parser.add_argument("--proj-name", help="Project name. ex: sidecar-redfish", required=True, choices=["sidecar-redfish", "inrow-cdu"]) 
arg_parser.add_argument("--env-file", help=".env file name", default="") # For testing
arg_parser.add_argument("--env", help="prod|stage|dev", default="") # For running app
# args = arg_parser.parse_args()
args, unknown = arg_parser.parse_known_args()

proj_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(proj_root)
ProjConstant.set_proj_root(proj_root)

if os.getenv("IS_TESTING_MODE") == "True": # if in testsing mode
    args.env = args.env or "test"
    
if args.env_file:
    # Top priority arg: `env-file`
    dotenv_path = ProjConstant.build_env_filepath(args.proj_name, args.env_file)
elif args.env in ["prod", ""]:
    # Default to `.env` for running app
    dotenv_path = ProjConstant.build_env_filepath(args.proj_name, ".env")
else:
    dotenv_path = ProjConstant.build_env_filepath(args.proj_name, f".env-{args.env}")  

print(f"Load env file: {dotenv_path}")  
load_dotenv(dotenv_path=dotenv_path, verbose=True, override=True)
os.environ["env"] = args.env

PROJECT_NAME = args.proj_name
os.environ["PROJ_NAME"] = args.proj_name

hardware_info: dict = {}
with open(os.path.join(proj_root, "etc", "hardware", f"{PROJECT_NAME}", "hardware_info.yaml"), encoding="utf-8") as f:
    hardware_info = yaml.safe_load(f)
    hardware_info["PowerSupplyCount"] = len(hardware_info.get("PowerSupplies",{}).keys())
    hardware_info["FanCount"] = len(hardware_info.get("Fans",{}).keys())
    hardware_info["FilterCount"] = len(hardware_info.get("Filters",{}).keys())
    hardware_info["PumpCount"] = len(hardware_info.get("Pumps",{}).keys())
    hardware_info["PrimaryCoolantConnectorCount"] = len(hardware_info.get("PrimaryCoolantConnectors",{}).keys())
    hardware_info["SecondaryCoolantConnectorCount"] = len(hardware_info.get("SecondaryCoolantConnectors",{}).keys())
    hardware_info["ValveCount"] = len(hardware_info.get("Valves",{}).keys())
    hardware_info["LeakDetectorCount"] = len(
        hardware_info.get("LeakDetectors", hardware_info.get("leak_detectors", {})).keys()
    )
    print("## hardware_info:")
    print(hardware_info)

redfish_info: dict = {}
with open(os.path.join(proj_root, "etc", "software", f"{PROJECT_NAME}", "redfish_info.yaml"), encoding="utf-8") as f:
    redfish_info = yaml.safe_load(f)
    print("## redfish_info:")
    print(redfish_info)
    
sensor_info: dict = {}
with open(os.path.join(proj_root, "etc", "sensor", f"{PROJECT_NAME}", "sensor_info.yaml"), encoding="utf-8") as f:
    sensor_info = yaml.safe_load(f)
    print("## sensor_info:")
    print(sensor_info)
    
registry_info: dict = {}
registry_info["Privilege"] = {}
with open(os.path.join(proj_root, "etc", "software", f"{PROJECT_NAME}", "Redfish_1.6.0_PrivilegeRegistry.json"), encoding="utf-8") as f:
    data = json.load(f)
    mappings = data.get("Mappings", [])
    for element in mappings:
        entity = element.get("Entity")
        if entity:
            # Exclude the "Entity" key from the value
            value = {k: v for k, v in element.items() if k != "Entity"}
            registry_info["Privilege"][entity] = value
    print("## Privilege Registry loaded")

registry_info["Base"] = {}
with open(os.path.join(proj_root, "etc", "software", f"{PROJECT_NAME}", "Base.1.21.0.json"), encoding="utf-8") as f:
    data = json.load(f)
    registry_info["Base"] = data
    print("## Base Registry loaded")