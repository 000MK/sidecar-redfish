from mylib.utils.load_api import load_raw_from_api, CDU_BASE


def ControlMode_change(new_mode):
    mapping = {
        "Automatic" : "auto",     
        "Manual"    : "manual",   
        "Disabled"  : "stop", 
        "Override"  : "override" 
    }
    
    reverse = {v: k for k, v in mapping.items()}
    bidict = {**mapping, **reverse}
    
    return bidict.get(new_mode)

def GetControlMode():
    mode = load_raw_from_api(f"{CDU_BASE}/api/v1/cdu/status/op_mode")["mode"]
    mapping = {
        "auto":     "Automatic",
        "manual":   "Manual",
        "stop":     "Disabled",
        "override": "Override",
        "inspection": "Manual"
    }
    ctrl = mapping.get(mode)
    return ctrl