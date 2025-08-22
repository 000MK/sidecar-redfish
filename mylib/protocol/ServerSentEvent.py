# from flask import Flask, Response, request, abort
# import json, time, redis, threading

# app = Flask(__name__)

# # Redis 設定
# REDIS_CHANNEL = "sse_events"
# r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# MAX_SSE_CONN = 5
# conn_counter = 0
# conn_lock = threading.Lock()

# # 模擬事件
# def event_producer():
#     i = 0
#     while True:
#         # print(f"[producer] 發送事件 EVT{i}")
#         time.sleep(5)
#         evt = {
#             "EventType": "TestEvent",
#             "EventId": f"EVT{i}",
#             "Message": f"Message {i}",
#             "EventTimestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
#         }
#         r.publish(REDIS_CHANNEL, json.dumps(evt))
#         i += 1

# # 啟用背景事件模擬
# def start_SSE_threading():
#     threading.Thread(target=event_producer, daemon=True).start()


# def event_stream(allowed_types=None):
#     global conn_counter
#     try:
#         with conn_lock:
#             if conn_counter >= MAX_SSE_CONN:
#                 abort(503, "Too many SSE connections")
#                 # return "test", 400
#             conn_counter += 1

#         pubsub = r.pubsub()
#         pubsub.subscribe(REDIS_CHANNEL)

    
#         for message in pubsub.listen():
#             if message['type'] != 'message':
#                 continue
#             evt = json.loads(message['data'])

#             # 篩選過濾
#             if allowed_types and evt.get("EventType") not in allowed_types:
#                 continue
            
#             yield f"event: {evt['EventType']}\n"
#             yield "data: " + json.dumps(evt) + "\n\n"
#     except Exception as e:
#         yield f"event: error\ndata: {str(e)}\n\n"
#     finally:
#         pubsub.close()
#         with conn_lock:
#             conn_counter -= 1

