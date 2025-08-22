"""
protocol = redfish
單純的TCP傳輸
配合redis來接收篩條件並傳輸
流程:
1.接收redis
2.檢查篩選條件
3.查詢符合條件的URI
4.傳輸
[規劃]
開機會把sqlite訂閱者存進cache 查詢時只要查cache不必重複查詢sqlite
POST PATCH DELETE會更改sqlite資料 成功後會同步至cache
"""
import requests
import json

# destination_url = "http://192.168.3.33:5000/eventreceiver"
# event_data = {
#     "@odata.type": "#Event.v1_4_0.Event",
#     "Events": [
#         {
#             "EventType": "Alert",
#             "Severity": "Critical",
#             "Message": "Fan 1 has failed.",
#             "EventId": "1001",
#             "MessageId": "FanFailure"
#         }
#     ]
# }
def send_event_redfish(destination_url, data):
    try:
        response = requests.post(
            destination_url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=5,
            verify=True  # 測試可關掉 SSL 驗證，上線要開
        )
        print(f"送出結果: {response.status_code} {response.text}")
    except Exception as e:
        print(f"推送失敗: {e}")


