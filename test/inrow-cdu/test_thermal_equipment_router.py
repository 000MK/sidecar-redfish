import os
import json
import pytest
import sys
import time
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from load_env import hardware_info
from typing import List
from mylib.utils.JsonUtil import JsonUtil
from test.reading_judger import ReadingJudgerPolicy3

cdu_id = 1

cdu_cnt = int(os.getenv("REDFISH_CDUS_COLLECTION_CNT", 1))
reservoir_cnt = int(os.getenv("REDFISH_RESERVOIR_COLLECTION_CNT", 1))
filter_cnt = int(hardware_info["FilterCount"])
primarycoolantconnector_cnt = int(hardware_info["PrimaryCoolantConnectorCount"])
secondarycoolantconnector_cnt = int(hardware_info["SecondaryCoolantConnectorCount"])
pump_cnt = int(hardware_info["PumpCount"])
leakdetector_cnt = int(hardware_info["LeakDetectorCount"])


def generate_pump_testcase(name: str, set_pump_id: int, setpoint: int, expected_infos: List[dict]):
    """
    @param set_pump_id: set pump id
    @param setpoint: setpoint value
    @param expected_infos: expected infos. 
        ex: [ {pump_id: 1, expected_value: 35}, {pump_id: 2, expected_value: 35} ]
    """
    _expected_infos = []
    endpoint = f'/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{set_pump_id}'
    for idx, info in enumerate(expected_infos):
        _expected_infos.append({
            "get.endpoint": f'/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{idx + 1}',
            # "payload.key": f"SpeedControlPercent.SetPoint",
            "response.key": f"PumpSpeedPercent.Reading",
            "expected_value": info["expected_value"]
        })
    return {
        "name": name,
        # 設定值
        "method": "PATCH",
        "endpoint": endpoint,
        "payload": {
            "SpeedControlPercent": {
                "SetPoint": int(setpoint),
                "ControlMode": "Manual"
            }
        },
        # 取得設定值
        "get.endpoint": endpoint,
        "get.assert_cases": [
            {"payload.key": "SpeedControlPercent.SetPoint", "response.key": "SpeedControlPercent.SetPoint"}
        ],
        # 取得sensor值
        "get.sensor.assert_cases": _expected_infos,
        "check_sensor.required": True
    }





beforehand_testcases = [
    # {
    #     "method": "PATCH",
    #     "endpoint": f'/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{sn}',
    #     "payload": {
    #         "SpeedControlPercent": {
    #             "SetPoint": 0,
    #             "ControlMode": "Manual"
    #         }
    #     },
    #     "get.endpoint": f'/redfish/v1/ThermalEquipment/CDUs/{cdu_id}/Pumps/{sn}',
    #     "get.assert_cases": [
    #         {"payload.key": "SpeedControlPercent.SetPoint", "response.key": "PumpSpeedPercent.Reading"},
    #     ],
    #     "check_sensor.required": False
    # }
    generate_pump_testcase(
        name=f"1-{sn}) pump停止，pump1,2轉速須為0",
        set_pump_id=sn, 
        setpoint=0, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 0}, {'pump_id': 2, 'expected_value': 0} ]
    )
    for sn in range(1, pump_cnt + 1)
]

rundown_test_cases_Pump = beforehand_testcases
rundown_test_cases_Pump += [
    generate_pump_testcase(
        name="2-1) pump1轉速設為35，pump1轉速須為35，pump2轉速須為0",
        set_pump_id=1, 
        setpoint=35, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 35}, {'pump_id': 2, 'expected_value': 0} ]
    ),
    generate_pump_testcase(
        name="2-2) pump1轉速設為70，pump1轉速須為70，pump2轉速須為0",
        set_pump_id=1, 
        setpoint=70, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 70}, {'pump_id': 2, 'expected_value': 0} ]
    ),
    generate_pump_testcase(
        name="2-3) pump1停止，pump1轉速須為0，pump2轉速須為0",
        set_pump_id=1, 
        setpoint=0, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 0}, {'pump_id': 2, 'expected_value': 0} ]
    ),
    generate_pump_testcase(
        name="3-1) pump2轉速設為35，pump1轉速須為0，pump2轉速須為35",
        set_pump_id=2, 
        setpoint=35, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 0}, {'pump_id': 2, 'expected_value': 35} ]
    ),
    generate_pump_testcase(
        name="3-2) pump2轉速設為70，pump2轉速須為70，pump2轉速須為0",
        set_pump_id=2, 
        setpoint=70, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 70}, {'pump_id': 2, 'expected_value': 0} ]
    ),
    generate_pump_testcase(
        name="3-3) pump2停止，pump1轉速須為0，pump2轉速須為0",
        set_pump_id=2, 
        setpoint=0, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 0}, {'pump_id': 2, 'expected_value': 0} ]
    ),
    generate_pump_testcase(
        name="4-1) pump1轉速設為35，pump1轉速須為35，pump2轉速須為0",
        set_pump_id=1, 
        setpoint=35, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 35}, {'pump_id': 2, 'expected_value': 0} ]
    ),
    generate_pump_testcase(
        name="4-2) pump2轉速設為70，pump1,2轉速須為70",
        set_pump_id=2, 
        setpoint=70, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 70}, {'pump_id': 2, 'expected_value': 70} ]
    ),
    generate_pump_testcase(
        name="4-3) pump2轉速設為35，pump1,2轉速須為35",
        set_pump_id=2, 
        setpoint=35, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 35}, {'pump_id': 2, 'expected_value': 35} ]
    ),
    generate_pump_testcase(
        name="5-1) pump1停止，pump1轉速須為0，pump2轉速須為35",
        set_pump_id=1, 
        setpoint=0, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 0}, {'pump_id': 2, 'expected_value': 35} ]
    ),
    generate_pump_testcase(
        name="5-2) pump2停止，pump1轉速須為0，pump2轉速須為0",
        set_pump_id=2, 
        setpoint=0, 
        expected_infos=[ {'pump_id': 1, 'expected_value': 0}, {'pump_id': 2, 'expected_value': 0} ]
    ),
]

##                                                                                                       
# PPPPPPPPPPPPPPPPP        AAA         TTTTTTTTTTTTTTTTTTTTTTT       CCCCCCCCCCCCCHHHHHHHHH     HHHHHHHHH
# P::::::::::::::::P      A:::A        T:::::::::::::::::::::T    CCC::::::::::::CH:::::::H     H:::::::H
# P::::::PPPPPP:::::P    A:::::A       T:::::::::::::::::::::T  CC:::::::::::::::CH:::::::H     H:::::::H
# PP:::::P     P:::::P  A:::::::A      T:::::TT:::::::TT:::::T C:::::CCCCCCCC::::CHH::::::H     H::::::HH
#   P::::P     P:::::P A:::::::::A     TTTTTT  T:::::T  TTTTTTC:::::C       CCCCCC  H:::::H     H:::::H  
#   P::::P     P:::::PA:::::A:::::A            T:::::T       C:::::C                H:::::H     H:::::H  
#   P::::PPPPPP:::::PA:::::A A:::::A           T:::::T       C:::::C                H::::::HHHHH::::::H  
#   P:::::::::::::PPA:::::A   A:::::A          T:::::T       C:::::C                H:::::::::::::::::H  
#   P::::PPPPPPPPP A:::::A     A:::::A         T:::::T       C:::::C                H:::::::::::::::::H  
#   P::::P        A:::::AAAAAAAAA:::::A        T:::::T       C:::::C                H::::::HHHHH::::::H  
#   P::::P       A:::::::::::::::::::::A       T:::::T       C:::::C                H:::::H     H:::::H  
#   P::::P      A:::::AAAAAAAAAAAAA:::::A      T:::::T        C:::::C       CCCCCC  H:::::H     H:::::H  
# PP::::::PP   A:::::A             A:::::A   TT:::::::TT       C:::::CCCCCCCC::::CHH::::::H     H::::::HH
# P::::::::P  A:::::A               A:::::A  T:::::::::T        CC:::::::::::::::CH:::::::H     H:::::::H
# P::::::::P A:::::A                 A:::::A T:::::::::T          CCC::::::::::::CH:::::::H     H:::::::H
# PPPPPPPPPPAAAAAAA                   AAAAAAATTTTTTTTTTT             CCCCCCCCCCCCCHHHHHHHHH     HHHHHHHHH
#
# @see https://patorjk.com/software/taag/#p=display&f=Doh&t=PATCH
## 
@pytest.mark.parametrize('testcase', rundown_test_cases_Pump)
def test_thermal_equipment_pump_run_down(client, basic_auth_header, testcase):
    """[TestCase] thermal_equipment pump run down"""
    index = rundown_test_cases_Pump.index(testcase) + 1
    print(f"## Running test case {index}/{len(rundown_test_cases_Pump)}: {testcase}")

    payload = testcase['payload']
    # 更新設定值
    print(f"## Update target value:")
    print(f"{testcase['method']} {testcase['endpoint']}")
    print(f"Payload: {payload}")
    # response = client.patch(testcase['endpoint'], headers=basic_auth_header, json=payload)
    http_method = getattr(client, testcase['method'].lower())
    response = http_method(testcase['endpoint'], headers=basic_auth_header, json=payload)
    print(f"Response json: {json.dumps(response.json, indent=2, ensure_ascii=False)}")
    assert response.status_code == 200
    print(f"PASS: {testcase['method']} {testcase['endpoint']} with payload {payload} is expected to return 200")


    # 取得設定值 (存於PLC的register)
    target_value = JsonUtil.get_nested_value(payload, 'SpeedControlPercent.SetPoint')
    wating_seconds = 1
    assert_field_success_cnt = 0
    assert_field_fail_cnt = 0
    print(f"## Waiting for configuration value: {target_value}")
    while wating_seconds < 30:
        assert_field_success_cnt = 0
        assert_field_fail_cnt = 0

        print(f"Wait {wating_seconds} seconds...")
        time.sleep(wating_seconds)
        wating_seconds = wating_seconds * 2
        print(f"GET {testcase['get.endpoint']}")
        response = client.get(testcase['get.endpoint'], headers=basic_auth_header)
        resp_json = response.json   
        print(f"Response json: {json.dumps(resp_json, indent=2, ensure_ascii=False)}")
        
        for assert_case in testcase['get.assert_cases']:
            target_value = JsonUtil.get_nested_value(payload, assert_case['payload.key'])
            resp_value = JsonUtil.get_nested_value(resp_json, assert_case['response.key'])
            if resp_value != target_value:
                assert_field_fail_cnt += 1
                print(f"... resp_value({resp_value}) != target_value({target_value}). Continue to wait ...")
                break
            assert_field_success_cnt += 1
        
        if assert_field_success_cnt == len(testcase['get.assert_cases']):
            print(f"Target value in PLC is updated successfully.")
            break
    
    assert assert_field_success_cnt == len(testcase['get.assert_cases'])
    print(f"PASS: GET {testcase['get.endpoint']} is expected resp_json.{assert_case['response.key']} == target_value ({target_value})")
    
    if not testcase['check_sensor.required']:
        return 
    
    # 取得sensor實際值 (注意，實際值不會這麼快就反應出來，通常要等待幾秒)
    print(f"## Wait for fan sensor value reaching the target value: {target_value}")
    # time.sleep(10)
    print(f"## Check Sensor Value:")
    sensor_assert_testcases = testcase['get.sensor.assert_cases']
    for sensor_assert_testcase in sensor_assert_testcases:
        try:
            endpoint = sensor_assert_testcase['get.endpoint']
            response = client.get(endpoint, headers=basic_auth_header)
            resp_json = response.json   
            # m = RfSensorFanExcerpt(**resp_json['Reading'])
            print(f"GET {endpoint}")
            print(f"Response json: {json.dumps(resp_json, indent=2, ensure_ascii=False)}")
            sensor_value = JsonUtil.get_nested_value(resp_json, sensor_assert_testcase['response.key'])

            judge_result = ReadingJudgerPolicy3(
                    client, 
                    uri=endpoint, 
                    basic_auth_header=basic_auth_header,
                    params={ 
                        "judge_sampling_interval": 1, 
                        "judge_sampling_cnt": 10, 
                        "is_dry_run": True }
                ).judge(target_value)
            print(f"Judge result: {judge_result}")
            assert judge_result['is_judge_success'] == True
            print(f"PASS: Judge reading value from policy3 is judged to {judge_result['is_judge_success']}.")
        
        except Exception as e:
            print(f"Error: {e}")
            raise e 
            
 


