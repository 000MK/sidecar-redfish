import pytest
import json
from flask import Flask

from mylib.services.rf_event_service import RfEventService


EventService_get_testcase = [
    {
        "endpoint" : "/redfish/v1/EventService",
        "assert_cases" : {
            "@odata.id" : "/redfish/v1/EventService",
            "@odata.type" : "#EventService.v1_11_0.EventService",
            "Id": "EventService",
            "Name": "Event Service",
            "@odata.context": "/redfish/v1/$metadata#EventService.EventService",
            "ExcludeRegistryPrefix" : False,
            "ExcludeMessageId" : False,
            "IncludeOriginOfConditionSupported" : False,
            "SubordinateResourcesSupported" : False,
            "SSEFilterPropertiesSupported" : {
                "RegistryPrefix" : True,
                "ResourceType" : True
            },
            "ServerSentEventUri" : "None",
            "ServiceEnabled" : True,
            "DeliveryRetryAttempts" : 3,
            "DeliveryRetryIntervalSeconds" : 60,
            "EventTypesForSubscription" : ["Alert"],
            "Subscriptions" : {
                "@odata.id" : "/redfish/v1/EventService/Subscriptions"
            },
            "Status" : {
                "Health" : "OK"
            }
        }
    }
]

Subscriptions_testcase = [
    {
        "endpoint": "/redfish/v1/EventService/Subscriptions",
        "assert_cases": {
            "@odata.id" : "/redfish/v1/EventService/Subscriptions",
            "@odata.type" : "#EventDestinationCollection.EventDestinationCollection",
            "@odata.context" : "/redfish/v1/$metadata#EventDestinationCollection.EventDestinationCollection",
            "Name" : "EventSubscriptions",
            "Description" : "Event Subscriptions Collection",
            "Members": [],
            "Members@odata.count": 1,
        }
    }
]

@pytest.mark.parametrize("testcase", EventService_get_testcase)
def test_eventservice_get_api(client, basic_auth_header, testcase):
    """[TestCase] EventService GET API"""
    
    print("## Get EventService:")
    print(f"\n## Running testcase:\n{json.dumps(testcase, indent=2, ensure_ascii=False)}")
    print(f"GET {testcase['endpoint']}")

    response = client.get(testcase['endpoint'], headers=basic_auth_header)
    assert response.status_code == 200
    data = response.get_json()
    print(f"Response json:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    assert_cases = testcase["assert_cases"]

    for key, expected in assert_cases.items():
        try:
            if isinstance(expected, dict):
                assert key in data
                for subkey, subval in expected.items():
                    assert subkey in data[key], f"{subkey} not in {key}"
                    assert data[key][subkey] == subval, f"{key}.{subkey} mismatch: expected {subval}, got {data[key][subkey]}"
                    print(f"PASS: {key}.{subkey} = {subval}")
            else:
                assert key in data, f"{key} missing in response"
                assert data[key] == expected, f"{key} mismatch: expected {expected}, got {data[key]}"
                print(f"PASS: {key} = {expected}")
        except AssertionError as e:
            print(f"Assertion failed for key '{key}': {e}")
            raise

@pytest.mark.parametrize("value", [True, False])
def test_eventservice_patch(client, basic_auth_header, value):
    """[TestCase] EventService PATCH API"""
    
    endpoint = "/redfish/v1/EventService"
    print("## Patch EventService:")
    print(f"## Running testcase: Set ServiceEnabled to {value}")
    print(f"## PATCH {endpoint} with payload: {{\"ServiceEnabled\": {value}}}")
    
    patch_resp = client.patch(endpoint, headers=basic_auth_header, json={"ServiceEnabled": value})
    print(f"Response status code: {patch_resp.status_code}")
    
    try:
        resp_json = patch_resp.get_json()
        if resp_json is not None:
            print(f"Response json:\n{json.dumps(resp_json, indent=2, ensure_ascii=False)}")
        else:
            print("No response body")
    except Exception:
        print("Response body is not valid JSON.")
        
    try:
        assert patch_resp.status_code in (200, 204)
        print(f"PASS: PATCH returned status code {patch_resp.status_code}")
    except AssertionError as e:
        print(f"FAIL: PATCH failed. {e}")
        raise e

@pytest.mark.parametrize("testcase", Subscriptions_testcase)
def test_subscriptions_get_api(client, basic_auth_header, testcase):
    """[TestCase] Subscriptions GET API"""
    
    print("## Get Subscriptions: ")
    print(f"\n## Running testcase:\n{json.dumps(testcase, indent=2, ensure_ascii=False)}")
    print(f"GET {testcase['endpoint']}")
    
    response = client.get(testcase['endpoint'], headers=basic_auth_header)
    assert response.status_code == 200
    resp_json = response.get_json()
    print(f"Response json:\n{json.dumps(resp_json, indent=2, ensure_ascii=False)}")
    assert_cases = testcase["assert_cases"]

    for key, value in assert_cases.items():
        try:
            if key == "Members@odata.count" :
                actual_count = resp_json.get("Members@odata.count" , 0)
                assert isinstance(actual_count, int) and actual_count >= 0
                print(f"PASS: {key} = {actual_count}")
            elif key == "Members":
                assert isinstance(resp_json[key], list), f"{key} should be a list"
                print(f"PASS: {key} is a list with {len(resp_json[key])} items")
            else:
                assert key in resp_json, f"{key} missing in response"
                assert resp_json.get(key) == value, f"{key} mismatch: {resp_json.get(key)} != {value}"
                print(f"PASS: {key} = {value}")
        except AssertionError as e:
            print(f"FAIL: '{key}': {e}")
            raise e
            
        
def test_subscriptions_id_get_all(client, basic_auth_header):
    """[TestCase] Subscriptions ID GET API"""
    
    print("\n## Testing endpoint: /redfish/v1/EventService/Subscriptions")
    print("## Running testcase: Get all subscriptions by ID")
    print("## GET /redfish/v1/EventService/Subscriptions")
    
    resp = client.get("/redfish/v1/EventService/Subscriptions", headers=basic_auth_header)
    assert resp.status_code == 200
    print(f"Response json:\n{json.dumps(resp.get_json(), indent=2, ensure_ascii=False)}")
    members = resp.get_json().get("Members", [])
    assert members, "應該至少有一筆訂閱資料"
    print(f"PASS: 共 {len(members)} 筆訂閱資料")

    for member in members:
        sub_uri = member["@odata.id"]
        sub_id = sub_uri.split("/")[-1]

        detail_resp = client.get(sub_uri, headers=basic_auth_header)
        assert detail_resp.status_code == 200, f"{sub_uri} 回傳非 200"
        print(f"PASS: {sub_uri} 回傳 200")

        data = detail_resp.get_json()
        print(f"Detail response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        expected_case = {
            "@odata.id": sub_uri,
            "@odata.type": "#EventDestination.v1_15_1.EventDestination",
            "DeliveryRetryPolicy": "RetryForever",
            "Destination": "127.0.0.1",
            "Id": sub_id,
            "Name": f"Event Subscription {sub_id}",
            "Protocol": "SNMPv2c",
            "RegistryPrefixes": [],
            "ResourceTypes": [],
            "SubscriptionType": "SNMPTrap",
            "Status": {"State": "Enabled", "Health": "OK"}
        }

        for key, value in expected_case.items():
            try:
                if key == "Status":
                    assert isinstance(data["Status"], dict)
                    state = data["Status"].get("State")
                    health = data["Status"].get("Health")
                    assert data["Status"]["State"] in ["Absent", "Enabled", "Disabled"]
                    assert data["Status"]["Health"] in ["OK", "Warning", "Critical"]
                    print(f"PASS: Status.State = {state}, Status.Health = {health}")
                    
                elif key in ["RegistryPrefixes", "ResourceTypes"]:
                    assert isinstance(data[key], list), f"{key} 應該是 list"
                    print(f"PASS: {key} 是 list")
                    
                else:
                    assert key in data, f"{key} not found in response"
                    assert data[key] == value, f"{key} 值不正確：{data[key]} != {value}"
                    print(f"PASS: {key} = {value}")
                    
            except AssertionError as e:
                print(f"FAIL: '{key}': {e}")
                raise e

def test_patch_subscriptions_id(client, basic_auth_header):
    """[TestCase] Subscriptions ID PATCH API"""
    
    print("## Patch a subscription by ID:")
    print("\n## Testing endpoint: /redfish/v1/EventService/Subscriptions")
    print("## Running testcase: Patch a subscription by ID")

    client.patch("/redfish/v1/EventService", headers=basic_auth_header, json={"ServiceEnabled": True})

    list_resp = client.get("/redfish/v1/EventService/Subscriptions", headers=basic_auth_header)
    assert list_resp.status_code == 200
    list_data = list_resp.get_json()
    print(f"Response JSON:\n{json.dumps(list_data, indent=2, ensure_ascii=False)}")

    members = list_data.get("Members", [])
    assert members, "No subscription data found"
    print(f"PASS: 共取得 {len(members)} 筆訂閱資料")

    sub_uri = members[0]["@odata.id"]

    patch_data = {
        "Destination": "127.0.0.1",
        "TrapCommunity": "public",
        "Context": "1"
    }
    patch_resp = client.patch(sub_uri, headers=basic_auth_header, json=patch_data)
    assert patch_resp.status_code == 200
    print(f"PASS: PATCH {sub_uri} 狀態碼為 200")

    try:
        patch_json = patch_resp.get_json()
        print("PATCH response JSON:\n", json.dumps(patch_json, indent=2, ensure_ascii=False))
    except Exception:
        print("PATCH response is not valid JSON.")
        print(patch_resp.get_data(as_text=True))

    get_resp = client.get(sub_uri, headers=basic_auth_header)
    assert get_resp.status_code == 200
    data = get_resp.get_json()
    print("GET response JSON:\n", json.dumps(data, indent=2, ensure_ascii=False))

    try:
        assert data["Destination"] == patch_data["Destination"], "Destination not match"
        print(f"PASS: Destination = {data['Destination']}")
        assert data["Context"] == patch_data["Context"], "Context not match"
        print(f"PASS: Context = {data['Context']}")
        
        assert "TrapCommunity" not in data, f"TrapCommunity shouldn't exist in response , but got:{data.get('TrapCommunity')}"
        print("PASS: TrapCommunity does not exist in response")
        
    except AssertionError as e:
        print(f"FAIL:  PATCH FAIL - {e}")
        raise e