import os
import json
import pytest
import sys
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .conftest import print_response_details

# from app import app
from load_env import hardware_info

'''
client定義在conftest.py裡
'''

env_testcases = [
    {
        "endpoint": '',
        "ProjectName": "sidecar-redfish",
        "assert_cases": {
            "ProjectName": "sidecar-redfish",
            "FanCount": 6,
            "PowerSupplyCount": 4,
            "PumpCount": 3,
            "ValveCount": 0
        }
    },
    {
        "endpoint": '',
        "ProjectName": "inrow-cdu",
        "assert_cases": {
            "ProjectName": "inrow-cdu",
            "FanCount": 0,
            "PowerSupplyCount": 4,
            "PumpCount": 2,
            "ValveCount": 5
        }
    },
]

@pytest.mark.parametrize('testcase', env_testcases)
def test_env_testcase(client, basic_auth_header, testcase):
    """[TestCase] env_testcase"""
    # response = client.get('/redfish')
    # print_response_details(response)
    
    args_project_name = os.getenv("PROJ_NAME")
    if args_project_name != testcase["ProjectName"]:
        return
    
    print(f"## Testing hardware_info of {testcase['ProjectName']}")
    for key, value in testcase["assert_cases"].items():
        try:
            print(f"Testing hardware_info[{key}] expected to be {value}")
            assert value == hardware_info[key]
            print(f"PASS: hardware_info[{key}] expected to be {value}")
        except Exception as e:
            print(f"FAIL: hardware_info[{key}] expected to be {value}, but actual is {hardware_info[key]}")
            raise e

