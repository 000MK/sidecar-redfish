'''
許多 API 都會有 ReadingUnits, Units 欄位，可能回傳 Unicode encoding
例如: "°C" 回傳 "\u00b0C"
本測試案例會測試所有 API 的 ReadingUnits, Units 欄位是否包含 Unicode encoding (不限於此)
'''
import os
import json
import pytest
import sys
import time
test_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(test_root)
from .conftest import print_response_details
from unittest.mock import MagicMock, patch
from http import HTTPStatus
from mylib.models.rf_resource_model import RfResetType
from mylib.models.rf_manager_model import RfResetToDefaultsType
from mylib.utils.DateTimeUtil import DateTimeUtil
from mylib.services.rf_telemetry_service import RfTelemetryService

chassis_id = 1

# testcases = [
#     {
#         "collections_endpoint" : f'/redfish/v1/Chassis/{chassis_id}/Sensors',
#         "endpoint" : f'/redfish/v1/Chassis/{chassis_id}/Sensors/%s',
#         "assert_cases" : {
#             "ReadingUnits": "(NOT contain character of '\u')",
#         }
#     },
#     {
#         ###
#         # Using curl to GET '/redfish/v1/TelemetryService/MetricDefinitions/coolant_supply_temperature' responds
#         # { ..., "Units": "\u00b0C" }
#         ###
#         "collections_endpoint" : f'/redfish/v1/TelemetryService/MetricDefinitions',
#         "endpoint" : f'/redfish/v1/TelemetryService/MetricDefinitions/%s',
#         "assert_cases" : {
#             "Units" : "(NOT contain character of '\u')",
#         },
#     }
# ]

no_unicode_testcases =[
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/conductivity",
        "assert_cases": {
            "Units": "µS/cm"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/ambient_temperature",
        "assert_cases": {
            "Units": "°C"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/coolant_supply_temperature",
        "assert_cases": {
            "Units": "°C"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/coolant_supply_temperature_spare",
        "assert_cases": {
            "Units": "°C"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/coolant_return_temperature",
        "assert_cases": {
            "Units": "°C"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/coolant_return_temperature_spare",
        "assert_cases": {
            "Units": "°C"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/target_coolant_temperature_setting",
        "assert_cases": {
            "Units": "°C"
        }
    },
    {
        "endpoint": "/redfish/v1/TelemetryService/MetricDefinitions/dew_point",
        "assert_cases": {
            "Units": "°C"
        }
    }
]

def test_all_metricdefinitions_units_no_unicode(client, basic_auth_header):
    """
    Test_all_metricdefinitions_units_no_unicode
    """
    print("## Get MetricDefinitions collection")
    collection_uri = "/redfish/v1/TelemetryService/MetricDefinitions"
    response = client.get(collection_uri, headers=basic_auth_header)
    assert response.status_code == 200, f"Failed to GET {collection_uri}"
    print(f"## Response status code: {response.status_code}")

    members = response.get_json().get("Members", [])
    assert members, "No Members found in MetricDefinitions"
    print(f"## Found {len(members)} members in MetricDefinitions")

    print(f"Found {len(members)} members")
    for member in members:
        uri = member.get("@odata.id")
        assert uri, "Missing @odata.id in member"
        print(f"\n## Checking {uri}")

        res = client.get(uri, headers=basic_auth_header)
        assert res.status_code == 200, f"Failed to GET {uri}"

        body_str = res.get_data(as_text=True)
        assert "\\u" not in body_str, f"{uri} response contains Unicode"

        json_data = res.get_json()
        for key in ["Units", "ReadingUnits"]:
            if key in json_data:
                value = json_data[key]
                print(f"{key}: {value}")
                assert "\\u" not in value, f"{uri} - {key} contains Unicode escape characters"
                print(f"PASS: {uri} - {key} does not contain Unicode")

# @pytest.mark.parametrize("testcase", testcases)
# def test_no_unicode_for_response_json(client, basic_auth_header, testcase):
#     """測試 API 回應的 json 中的 unit 欄位是否包含 Unicode encoding"""
#     ... 