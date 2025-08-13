import os
import json
import pytest
import sys
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from load_env import hardware_info, redfish_info
from .conftest import AssertChecker, AssertType
from mylib.utils.JsonUtil import JsonUtil

cdu_id = 1

cdu_cnt = int(os.getenv("REDFISH_CDUS_COLLECTION_CNT", 1))
reservoir_cnt = int(os.getenv("REDFISH_RESERVOIR_COLLECTION_CNT", 1))
filter_cnt = int(hardware_info["FilterCount"])
primarycoolantconnector_cnt = int(hardware_info["PrimaryCoolantConnectorCount"])
secondarycoolantconnector_cnt = int(hardware_info["SecondaryCoolantConnectorCount"])
pump_cnt = int(hardware_info["PumpCount"])
leakdetector_cnt = int(hardware_info["LeakDetectorCount"])

thermal_equipment_reserviors_testcases = [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Reservoirs",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Reservoirs",
            "@odata.type": "#ReservoirCollection.ReservoirCollection",
            "Members@odata.count": reservoir_cnt,
            "Members": [
                {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Reservoirs/{sn}"}
                for sn in range(1, reservoir_cnt + 1)
            ],
        }
    }
] + [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Reservoirs/{sn}",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Reservoirs/{sn}",
            "@odata.type": "#Reservoir.v1_0_0.Reservoir",
        }
    }
    for sn in range(1, reservoir_cnt + 1)
]

thermal_equipment_leakdetection_testcases = [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/LeakDetection",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/LeakDetection",
            "@odata.type": "#LeakDetection.v1_1_0.LeakDetection",
        }
    }, {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/LeakDetection/LeakDetectors",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/LeakDetection/LeakDetectors",
            "@odata.type": "#LeakDetectorCollection.LeakDetectorCollection",
            "Members@odata.count": leakdetector_cnt,
        }
    }
]


thermal_equipment_filters_testcases = [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters",
            "@odata.type": "#FilterCollection.FilterCollection",
            "Members@odata.count": filter_cnt,
            "Members": [
                {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters/{sn}"}
                for sn in range(1, filter_cnt + 1)
            ],
        }
    }
] + [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters/{sn}",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Filters/{sn}",
            "@odata.type": "#Filter.v1_0_2.Filter",
            "@odata.context": "/redfish/v1/$metadata#Filter.Filter",
            "ServiceHours": -1,
        }
    }
    for sn in range(1, filter_cnt + 1)
]

thermal_equipment_basic_testcases = [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs",
        "assert_cases": { # 代表這個endpoint的response json要測以下三項
            "@odata.id": "/redfish/v1/ThermalEquipment/CDUs",
            "@odata.type": "#CoolingUnitCollection.CoolingUnitCollection",
            "@odata.context": "/redfish/v1/$metadata#CoolingUnitCollection.CoolingUnitCollection",

            "Members@odata.count": cdu_cnt,
            "Members": [
                {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{sn}"}
                for sn in range(1, cdu_cnt + 1)
            ],
        }
    },
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors",
        "assert_cases": { # 代表這個endpoint的response json要測以下三項
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors",
            "@odata.type": "#CoolantConnectorCollection.CoolantConnectorCollection",
            "Members@odata.count": primarycoolantconnector_cnt,
            "Members": [
                {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/PrimaryCoolantConnectors/{sn}"}
                for sn in range(1, primarycoolantconnector_cnt + 1)
            ],
        }
    },
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/EnvironmentMetrics",
        "assert_cases": { 
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/EnvironmentMetrics",
            "@odata.type": "#EnvironmentMetrics.v1_3_2.EnvironmentMetrics",
        }
    },
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps",
        "assert_cases": { # 代表這個endpoint的response json要測以下三項
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps",
            "@odata.type": "#PumpCollection.PumpCollection",
            "Members@odata.count": pump_cnt,
            "Members": [
                {"@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{sn}"}
                for sn in range(1, pump_cnt + 1)
            ],
        }
    }
] + [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{sn}",
        "assert_cases": {
            "@odata.id": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{sn}",
            "@odata.type": "#Pump.v1_2_0.Pump",
            "Id": f"{sn}",
        }
    } 
    for sn in range(1, pump_cnt + 1)
]

# 專測回傳的值是否正確
thermal_equipment_detail_value_testcases = [
    # {
    #     "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}",
    #     "assert_cases": { # 代表這個endpoint的response json要測以下三項
    #         "@odata.id": "/redfish/v1/ThermalEquipment/CDUs",
    #         "@odata.type": "#CoolingUnitCollection.CoolingUnitCollection",
    #         "@odata.context": "/redfish/v1/$metadata#CoolingUnitCollection.CoolingUnitCollection",
    #     }
    # },
    {
        "description": "inrow-cdu的SecondaryCoolantConnectors需要測，sidecar的PrimaryCoolantConnectors需要測",
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/SecondaryCoolantConnectors/1",
        "assert_cases": [
            { 
                "resp_key_path": "SupplyTemperatureControlCelsius.AllowableMax",
                "expected_value": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.max")
            },
            { 
                "resp_key_path": "SupplyTemperatureControlCelsius.AllowableMin",
                "expected_value": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.SupplyTemperatureControlCelsius.min")
            },
            { 
                "resp_key_path": "DeltaPressureControlkPa.AllowableMax",
                "expected_value": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.max")
            },
            { 
                "resp_key_path": "DeltaPressureControlkPa.AllowableMin",
                "expected_value": JsonUtil.get_nested_value(redfish_info, "Settings.DefaultAllowableRange.DeltaPressureControlkPa.min")
            },
        ]
    },
]

thermal_equipment_testcases = thermal_equipment_basic_testcases
# thermal_equipment_testcases += thermal_equipment_reserviors_testcases 
thermal_equipment_testcases += thermal_equipment_leakdetection_testcases
thermal_equipment_testcases += thermal_equipment_filters_testcases


@pytest.mark.parametrize('testcase', thermal_equipment_testcases)
def test_thermal_equipment_api(client, basic_auth_header, testcase):
    """[TestCase] thermal_equipment API"""
    print(f"GET {testcase['endpoint']}")
    response = client.get(testcase['endpoint'], headers=basic_auth_header)
    resp_json = response.json
    print(f"Response: {json.dumps(resp_json, indent=2, ensure_ascii=False)}")
    assert response.status_code == 200
    
    for key, value in testcase['assert_cases'].items():
        # Members比較特殊，排序後確認內容
        try:
            print(f"Testing resp_json[{key}] expected to be {value}")
            if key == "Members":
                resp_json[key] = sorted(resp_json[key], key=lambda x: x['@odata.id'])
                assert resp_json[key] == value
            elif key == "Status":
                assert isinstance(resp_json["Status"], dict)
                # assert resp_json["Status"]["State"] in ["Absent", "Enabled", "Disabled"]
                assert resp_json["Status"]["Health"] in ["OK", "Warning", "Critical"]
            elif key == "ServiceHours":
                assert AssertChecker.check(AssertType.VALUE_GT_0, resp_json[key], 0)
            else:
                assert AssertChecker.check(AssertType.CONSTANT, resp_json[key], value)
            print(f"PASS: resp_json[{key}] expected to be {value}")
        except AssertionError as e:
            print(f"FAIL: AssertionError: {e}, key: {key}, value: {value}")
            raise e
            
 


redundant_testcases = [
    {
        "endpoint": f"/redfish/v1/ThermalEquipment/CDUs/9999",
    },
]
@pytest.mark.parametrize('redundant_testcase', redundant_testcases)
def test_redundant_thermal_equipment_api(client, basic_auth_header, redundant_testcase):
    """測試，如果uri不存在，應該回傳相對應的httpstatus"""
    try:
        print(f"Endpoint: {redundant_testcase['endpoint']}")
        response = client.get(redundant_testcase['endpoint'], headers=basic_auth_header)
        resp_json = response.json
        print(f"Response json: {json.dumps(resp_json, indent=2, ensure_ascii=False)}")
        assert response.status_code == 404
        print(f"PASS: Endpoint: {redundant_testcase['endpoint']} is expected to return 404")
    except Exception as e:
        print(f"FAIL: Endpoint: {redundant_testcase['endpoint']} is expected to return 404, but got {e}")
        raise e


@pytest.mark.parametrize('testcase', thermal_equipment_detail_value_testcases)
def test_thermal_equipment_detail_value_api(client, basic_auth_header, testcase):
    """[TestCase] thermal_equipment API"""
    print(f"GET {testcase['endpoint']}")
    response = client.get(testcase['endpoint'], headers=basic_auth_header)
    resp_json = response.json
    print(f"Response: {json.dumps(resp_json, indent=2, ensure_ascii=False)}")
    assert response.status_code == 200
    
    succ_cnt = 0
    fail_cnt = 0
    for assert_case in testcase['assert_cases']:
        resp_key_path = assert_case['resp_key_path']
        expected_value = assert_case['expected_value']
        try:
            print(f"+ Testing resp_json[{resp_key_path}] expected to be {expected_value}")
            actual_value = JsonUtil.get_nested_value(resp_json, resp_key_path)
            assert actual_value == expected_value
            print(f"  PASS: resp_json[{resp_key_path}] expected to be {expected_value}")
            succ_cnt += 1
        except AssertionError as e:
            print(f"  FAIL: AssertionError: {e}, key: {resp_key_path}, value: {expected_value}")
            fail_cnt += 1
    
    print(f"Test result: succ_cnt={succ_cnt}, fail_cnt={fail_cnt}")
    assert fail_cnt == 0