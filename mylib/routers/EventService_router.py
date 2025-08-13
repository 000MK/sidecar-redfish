import os
from flask import current_app, request, jsonify, make_response, send_file, Response, abort
from flask_restx import Namespace, Resource, fields

from mylib.services.rf_event_service import RfEventService
from mylib.common.my_resource import MyResource
from mylib.common.proj_error import ProjRedfishError, ProjRedfishErrorCode
from http import HTTPStatus

EventService_ns = Namespace('', description='EventService Collection')

# =============================================
# 驗證器
# =============================================
# class MyBaseEventService(MyResource):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.Subscriptions_id_count = 10
    
#     def _validate_request(self):
#         try:
#             Subscriptions_id = request.view_args.get("Subscriptions_id")
            
#             if not self._is_valid_id(Subscriptions_id, self.Subscriptions_id_count):
#                 abort(HTTPStatus.NOT_FOUND, description=f"Subscriptions_id, {Subscriptions_id}, not found")
#         except Exception as e:
#             abort(HTTPStatus.NOT_FOUND, description=f"[Unexpected Error] {e}")
    
#     def _is_valid_id(self, id: str, max_value: int):
#         if id: # request有傳id進來才檢查
#             if not id.isdigit():
#                 return False
#             if not (0 < int(id) <= max_value):
#                 return False
#         return True
# =============================================
# patch/post model
# =============================================
# EventService patch設置
EventService_patch = EventService_ns.model('EventServicePatch', {
    'ServiceEnabled': fields.Boolean(
        # required=True,
        description='ServiceEnabled',
        default=True,
        example=True
    ),
    # "DeliveryRetryAttempts": fields.Integer(
    #     # required=True,
    #     description='DeliveryRetryAttempts',
    #     default=True,
    #     example=3
    # ),
    # "DeliveryRetryIntervalSeconds": fields.Integer(
    #     # required=True,
    #     description='DeliveryRetryIntervalSeconds',
    #     default=True,
    #     example=60
    # )
})

# Event Subscription psot設置
EventSubscription_post = EventService_ns.model('EventSubscriptionPost', {
    # essential
    'Destination': fields.String(
        required=True,
        description='URI',
        default=True,
        example="127.0.0.1"
    ),
    "Protocol": fields.String(
        required=True,
        description='Protocol',
        default=True,
        example="SNMPv2c",
        enum = ["SNMPv2c"]
        # enum=["Redfish", "Kafka", "SNMPv1", "SNMPv2c", "SNMPv3", "SMTP", "SyslogTLS", "SyslogTCP", "SyslogUDP", "SyslogRELP", "OEM"]
    ),
    "Context": fields.String(
        required=True,
        description='Context',
        default=True,
        example="1"
    ),
    # optional
    "SubscriptionType": fields.String(
        # required=True,
        description='SubscriptionType',
        default=True,
        example="SNMPTrap",
        eumu=["SNMPTrap"]
        # eumu=["SNMPTrap", "RedfishEvent", "SNMPTrap", "SNMPInform", "SSE", "OEM"]
    ),
    "TrapCommunity": fields.String(
        # required=True,
        description='TrapCommunity',
        default=True,
        example="public"
    ),
    "DeliveryRetryPolicy": fields.String(
        # required=True,
        description='DeliveryRetryPolicy',
        default=True,
        example="TerminateAfterRetries",
        enum=["RetryForever", "TerminateAfterRetries", "SuspendRetries"]
    ),
    "RegistryPrefixes": fields.List(
        fields.String,
        # required=True,
        description='RegistryPrefixes',
        default=True,
        example=[]
    ),
    "ResourceTypes": fields.List(
        fields.String,
        # required=True,
        description='ResourceTypes',
        default=True,
        example=[]
    ),
    "EventFormatType": fields.String(
        # required=True,
        description='EventFormatType',
        default=True,
        example="Event",
        enum=["Event", "MetricReport"]
    ),
    "Severities": fields.List(
        fields.String,
        # required=True,
        description='Severities',
        default=True,
        example=["Critical", "Warning", "OK", "Informational"],
        enum=["Critical", "Warning", "OK", "Informational"]
    ),
    # SubordinateResources 確認此資源

})
# Event Subscription Id patch設置
EventSubscriptionId_patch = EventService_ns.model('EventSubscriptionIdPatch', {
    # essential
    # 'Destination': fields.String(
    #     required=True,
    #     description='URI',
    #     default=True,
    #     example="127.0.0.1"
    # ),
    # 'TrapCommunity': fields.String(
    #     required=True,
    #     description='TrapCommunity',
    #     default=True,
    #     example="public"
    # ),
    "Context": fields.String(
        required=True,
        description='Context',
        default=True,
        example="1"
    ),
    "DeliveryRetryPolicy": fields.String(
        # required=True,
        description='DeliveryRetryPolicy',
        default=True,
        example="TerminateAfterRetries",
        enum=["RetryForever", "TerminateAfterRetries", "SuspendRetries"]
    ),
    # 研究下面兩個是甚麼
    # "HttpHeaders": fields.List(
    #     fields.String,
    #     # required=True,
    #     description='HttpHeaders',
    #     default=True,
    #     example=[]
    # ),
    # "BackupDestinations": fields.List(
    #     fields.String,
    #     # required=True,
    #     description='BackupDestinations',
    #     default=True,
    #     example=[]
    # ),
})

# =============================================
# route
# =============================================
@EventService_ns.route("/EventService")
class EventService(Resource):
    # menthod get/patch
    def get(self):
        # return EventService_data
        return RfEventService().get_event_service()
    
    @EventService_ns.expect(EventService_patch, validate=True)
    def patch(self):
        body = request.get_json(force=True)
        return RfEventService().patch_event_service(body)


@EventService_ns.route("/EventService/Subscriptions")
class Subscriptions(Resource):
    # get/post
    def get(self):
        # return Subscriptions_data    
        return RfEventService().get_subscriptions()
    
    @EventService_ns.expect(EventSubscription_post, validate=True)
    def post(self):
        body = request.get_json(force=True)
        resp = RfEventService().post_subscriptions(body)
        # location = resp["@odata.id"]
        return resp #, {"Location": location}

    
@EventService_ns.route("/EventService/Subscriptions/<string:Subscriptions_id>")
class Subscriptions(Resource):
    # get/delete/patch
    def get(self, Subscriptions_id):
        # return Subscriptions_id_data        
        return RfEventService().get_subscriptions_id(Subscriptions_id)
    
    @EventService_ns.expect(EventSubscriptionId_patch, validate=True)
    def patch(self, Subscriptions_id):
        body = request.get_json(force=True)
        return RfEventService().patch_subscriptions_id(Subscriptions_id, body)
    
    def delete(self, Subscriptions_id):
        return RfEventService().delete_subscriptions_id(Subscriptions_id)
    
# @EventService_ns.route("/EventService/SSE")   
# class ServerSentEvent(Resource):
#     def get(self):
#         return RfEventService().subscriptions_SSE()    