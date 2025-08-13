'''
這是Redfish的event service
'''
import subprocess, json
import requests
import ipaddress
from flask import jsonify, Response
from mylib.services.base_service import BaseService
from mylib.models.rf_networkprotocol_model import RfNetworkProtocolModel
from mylib.models.rf_snmp_model import RfSnmpModel
from mylib.adapters.webapp_api_adapter import WebAppAPIAdapter
from mylib.models.rf_resource_model import RfResetType
from mylib.common.proj_response_message import ProjResponseMessage
from mylib.utils.load_api import load_raw_from_api, CDU_BASE
from mylib.models.rf_event_service_model import RfEventServiceModel, RfEventSubscriptionsModel, RfEventSubscriptionIdModel
from mylib.models.rf_status_model import RfStatusModel
from mylib.models.setting_model import SettingModel
from mylib.models.setting_subscriptions_model import SubscriptionModel
# from mylib.utils.ServerSentEvent import event_stream#, clear_subscribers
from mylib.common.proj_error import ProjRedfishError, ProjRedfishErrorCode
from load_env import redfish_info


class RfEventService(BaseService):
    #==========================================
    # 共用函數
    #==========================================
    def get_ServiceEnabled(self):
        """
        取得 EventService 的啟用狀態
        :return: True 或 False
        """
        return bool(int(SettingModel().get_by_key("EventService.ServiceEnabled").value))
    
    def save_ServiceEnabled(self, value):
        """
        設定 EventService 的啟用狀態
        :return: True 或 False
        """
        return SettingModel().save_key_value("EventService.ServiceEnabled", value)
    
    def get_eventservice_setting(self, key: str):
        """
        取得 EventService 的設定值
        :param key: 設定的鍵名
        :return: 設定的值
        """
        return int(SettingModel().get_by_key(f"EventService.{key}").value)
    
    def save_eventservice_setting(self, key: str, value: str):
        """
        儲存 EventService 的設定到資料庫
        :param key: 設定的鍵名
        :param value: 設定的值
        :return: True 或 False
        """
        return SettingModel().save_key_value(f"EventService.{key}", value)
    
    def save_Subscription(self, data: dict):
        """
        儲存訂閱資料到資料庫
        :param data: 訂閱資料字典
        :return: Id
        """
        return SubscriptionModel.sub_post(data)
    
    def get_Subscription_data(self, sub_id: str):
        """
        取得指定訂閱 ID 的訂閱資料
        :param sub_id: 訂閱 ID
        :return: Dict 或 None
        """
        data = SubscriptionModel.sub_get_by_id(sub_id)
        if data is None:
            return None
        if not isinstance(data, dict):
            data = {col.name: getattr(data, col.name) for col in data.__table__.columns}
        return data
    
    def get_Subscription_all(self):
        """
        取得所有訂閱資料
        :return: 訂閱物件列表
        """
        return SubscriptionModel.sub_all()
    
    def Setting_snmp(self, trap_ip_address: str, read_community: str) -> dict:
        data = {
            "trap_ip_address": trap_ip_address,
            "read_community":  read_community,
        }
        try:
            r = WebAppAPIAdapter().setting_snmp(data)
            return jsonify({ "message": r.text })      
            # return r.json(), r.status_code
        except requests.HTTPError as e:
            # 如果 CDU 回了 4xx/5xx，直接把它的 status code 和 body 回來
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.INTERNAL_ERROR, 
                message=f"WebAppAPIAdapter#setting_snmp() FAIL: data={data}, details={str(e)}"
            )

        except requests.RequestException as e:
            # 純粹網路／timeout／連線失敗
            raise ProjRedfishError(
                code=ProjRedfishErrorCode.SERVICE_TEMPORARILY_UNAVAILABLE, 
                message=f"WebAppAPIAdapter#setting_snmp() FAIL: data={data}, details={str(e)}"
            )
            
    # 檢查 IP
    def is_valid_ip(self,addr: str) -> bool:
        try:
            ipaddress.ip_address(addr)
            return True
        except ValueError:
            return False
    #==========================================
    # EventService
    #==========================================
    def get_event_service(self):
        m = RfEventServiceModel()
        m.ExcludeMessageId = False
        m.ExcludeRegistryPrefix = False
        m.IncludeOriginOfConditionSupported = False
        m.SubordinateResourcesSupported = False
        m.ServiceEnabled = self.get_ServiceEnabled()
        m.DeliveryRetryAttempts = self.get_eventservice_setting("DeliveryRetryAttempts") 
        m.DeliveryRetryIntervalSeconds = self.get_eventservice_setting("DeliveryRetryIntervalSeconds")
        m.EventTypesForSubscription = ["Alert"]
        m.ServerSentEventUri = "None"
        SSEFilterPropertiesSupported = {
            "RegistryPrefix": True,
            "ResourceType": True
        }
        m.SSEFilterPropertiesSupported = RfEventServiceModel._SSEFilterPropertiesSupported(**SSEFilterPropertiesSupported)
        m.ResourceTypes = []
        m.RegistryPrefixes=[]
        m.Subscriptions = {
            "@odata.id": "/redfish/v1/EventService/Subscriptions"
        }
        status = {
            "State": "Enabled" if self.get_ServiceEnabled() else "Disabled",
            "Health": "OK"
        }
        m.Status = RfStatusModel(**status)
        
        return m.to_dict(), 200
    
    def patch_event_service(self, body):
        '''
        ServiceEnabled: 是否啟用服務
        DeliveryRetryAttempts: 重試次數
        DeliveryRetryIntervalSeconds: 重試間隔
        '''
        ServiceEnabled = body.get("ServiceEnabled")
        DeliveryRetryAttempts = body.get("DeliveryRetryAttempts")
        DeliveryRetryIntervalSeconds = body.get("DeliveryRetryIntervalSeconds")
        if ServiceEnabled is not None:
            if ServiceEnabled is True:
                s = 1
            
            if ServiceEnabled == False:
                # clear_subscribers() # 清除所有 SSE 訂閱者
                s = 0
                self.Setting_snmp("", "")
            self.save_ServiceEnabled(s)      

        if DeliveryRetryAttempts is not None:
            self.save_eventservice_setting("DeliveryRetryAttempts", DeliveryRetryAttempts)
        if DeliveryRetryIntervalSeconds is not None:
            self.save_eventservice_setting("DeliveryRetryIntervalSeconds", DeliveryRetryIntervalSeconds)
            
        return self.get_event_service()
    #==========================================
    # EventSubscriptions
    #==========================================
    def get_subscriptions(self):
        m = RfEventSubscriptionsModel()
        all_subscriptions = self.get_Subscription_all()
        m.Members_odata_count = len(all_subscriptions)
        for sub in all_subscriptions:
            m.Members.append({
                "@odata.id": f"/redfish/v1/EventService/Subscriptions/{sub.Id}"
            })
        
        return m.to_dict(), 200
    
    def post_subscriptions(self, body): # 要新增各種協議驗證 以protocol為主
        RegistryPrefixes = body.get("RegistryPrefixes", None)
        ResourceTypes = body.get("ResourceTypes", None)
        Destination = body.get("Destination")
        
        POST_SUBSCRIPTION_ACCOUNT_LIMIT = redfish_info.get("Settings", {}).get("POSTSubscriptionLimit", 10)
        all_post_subscription = self.get_Subscription_all()
        if len(all_post_subscription) >= POST_SUBSCRIPTION_ACCOUNT_LIMIT:
            return {
                "ProjRedfishError": f"Subscription limit has been reached (max {POST_SUBSCRIPTION_ACCOUNT_LIMIT})."
            }, 400
        
        # 檢查 IP 格式 (有些是輸入網址或port號 無法通過)
        if self.is_valid_ip(Destination) is False:
            return {"error": "Invalid IP address format"}, 400
        if RegistryPrefixes is not None:
            if len(RegistryPrefixes) == 0:
                body["RegistryPrefixes"] = None
        if ResourceTypes is not None:
            if len(ResourceTypes) == 0:
                body["ResourceTypes"] = None

        # 存入資料庫
        Id = self.save_Subscription(body)
        output_data = self.get_subscriptions_id(Id)
        
        db_data = self.get_Subscription_data(Id)
        # protocol 設定
        if body["Protocol"] == "SNMPv2c":
            trap = db_data.get("Settings", {}).get("TrapCommunity")
            self.Setting_snmp(db_data["Destination"], trap)
            
        location = output_data["@odata.id"]
        # return resp, {"Location": location}    
        return output_data, {"Location": location}  
    
    #==========================================
    # EventSubscriptionId
    #==========================================
    def get_subscriptions_id(self, subscription_id: str):
        m = RfEventSubscriptionIdModel(Subscriptions_id=subscription_id)
        sub_data = self.get_Subscription_data(subscription_id)
        if sub_data is None:
            return {"error": "Subscription not found"}, 404
        m.SubscriptionType = sub_data["SubscriptionType"]
        m.Context = sub_data["Context"] 
        m.DeliveryRetryPolicy = sub_data["DeliveryRetryPolicy"] 
        m.Destination = sub_data["Destination"]
        m.Protocol = sub_data["Protocol"] 
        m.EventFormatType = sub_data["EventFormatType"] 
        m.RegistryPrefixes = sub_data["RegistryPrefixes"] 
        m.ResourceTypes = sub_data["ResourceTypes"] 
        status = {
            "State": "Enabled" if self.get_ServiceEnabled() else "Disabled",
            "Health": "OK"
        }
        m.Status = RfStatusModel(**status)
        
        return m.to_dict()
    
    def patch_subscriptions_id(self, subscription_id: str, body):       
        sub_data = self.get_Subscription_data(subscription_id)
        # 檢查是否有這筆資料
        if sub_data is None:
            return {"error": "Subscription not found"}, 404
        
        # 更新資料
        update_sub = {
            "Context",
            "DeliveryRetryPolicy",
            # "HttpHeaders",
            # "BackupDestinations"
        } 
        for key in update_sub:
            if key in body:
                sub_data[key] = body[key]
                
        # 存進資料庫
        self.save_Subscription(sub_data)
        return self.get_subscriptions_id(subscription_id)
    
    def delete_subscriptions_id(self, subscription_id: str):
        """
        刪除指定訂閱 ID 的訂閱資料
        :param subscription_id: 訂閱 ID
        :return: 成功訊息或錯誤訊息
        """
        sub = self.get_Subscription_data(subscription_id)
        if not sub:
            return {"error": "Subscription not found"}, 404
        
        SubscriptionModel.sub_delete(subscription_id)
        return {"message": "Subscription deleted successfully"}, 200
    
    #==========================================
    # ServerSentEvent
    #==========================================   
    # def subscriptions_SSE(self): 
    #     """
    #     1.先判斷EventService是否有啟動
    #     2.取得要過濾的事件
    #     3.設定SSE發送事件
    #     """
    #     if self.get_ServiceEnabled() is not True:
    #         # clear_subscribers()
    #         return {"error": "EventService not Enabled"}
    
    #     # 過濾條件
    #     filters = {}
    #     return Response(event_stream(filters), mimetype="text/event-stream")        