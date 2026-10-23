"""
主服务器模块 / โมดูลเซิร์ฟเวอร์หลัก (Main Server)
基于 Flask 提供 LINE Webhook API 端点，接收群聊/私聊消息并自动翻译回复
รันเซิร์ฟเวอร์ Flask รับ Webhook จาก LINE แปลภาษาอัตโนมัติและตอบกลับในกลุ่ม/แชท
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import threading

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, TextMessage, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

import config
from translator import translate_message

app = Flask(__name__)

# 初始化 LINE SDK 配置 / กำหนดค่าการเชื่อมต่อ LINE SDK
configuration = Configuration(access_token=config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(config.LINE_CHANNEL_SECRET)

# 异步线程池与消息防重缓存 / Thread pool & deduplication
executor = ThreadPoolExecutor(max_workers=10)


class MessageDeduplicator:
    def __init__(self, capacity=500):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def is_duplicate(self, msg_id: str) -> bool:
        if not msg_id:
            return False
        with self.lock:
            if msg_id in self.cache:
                return True
            self.cache[msg_id] = True
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            return False


deduplicator = MessageDeduplicator()


def process_webhook_async(body: str, signature: str):
    """
    后台线程执行事件解析与业务处理，避免阻塞 Webhook 导致 LINE 超时 (499)
    """
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"[Webhook 异步异常 / ข้อผิดพลาด Webhook] {e}")


@app.route("/line/callback", methods=['POST'])
def callback():
    """
    LINE Webhook 回调入口，快速校验签名并异步分发事件
    จุดรับ Webhook จาก LINE ตรวจสอบลายเซ็นดิจิทัลและส่งต่อเหตุการณ์แบบอะซิงโครนัส
    """
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    if signature is None:
        return 'Missing Signature', 400

    # 1. 快速校验签名（耗时约 0.05ms），防恶意请求
    if not handler.parser.signature_validator.validate(body, signature):
        print("[LINE 错误 / ข้อผิดพลาด] 签名验证失败 / ตรวจสอบลายเซ็นไม่ผ่าน (Invalid Signature)")
        abort(400)

    # 2. 异步派发至线程池处理，立即向 LINE 返回 200 OK，防止 499 超时断开
    executor.submit(process_webhook_async, body, signature)
    return 'OK', 200


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """
    处理收到的文本消息（支持群聊与私聊）
    ประมวลผลข้อความตัวอักษรที่ได้รับ (รองรับทั้งกลุ่มและแชทส่วนตัว)
    """
    msg_id = getattr(event.message, 'id', None)
    if msg_id and deduplicator.is_duplicate(msg_id):
        print(f"[消息防重] 忽略重复消息 ID: {msg_id}")
        return

    msg = event.message.text.strip()
    source_type = getattr(event.source, 'type', 'unknown') if hasattr(event, 'source') else 'unknown'
    user_id = getattr(event.source, 'user_id', 'unknown') if hasattr(event, 'source') else 'unknown'

    reply_text = translate_message(msg)

    if reply_text:
        print(f"[消息处理 / ประมวลผลข้อความ] 来源: {source_type} (用户: {user_id[:8]}...)\n原文: {msg}\n{reply_text}")
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_text)]
                    )
                )
            print("[LINE 回复成功 / ส่งข้อความตอบกลับสำเร็จ]")
        except Exception as e:
            print(f"[LINE 回复失败 / ส่งข้อความตอบกลับไม่สำเร็จ] {e}")
    else:
        # 当文本非中泰（如纯英文、数字、系统指令）时记录，方便排查
        print(f"[忽略消息 / ข้ามข้อความ] 来源: {source_type} | 原文无需翻译: {msg}")


if __name__ == "__main__":
    # 启动前自检 / ตรวจสอบความถูกต้องก่อนเริ่มระบบ
    config.validate_config()
    print("=" * 60)
    print("🚀 LINE 翻译机器人启动中... / บอตแปลภาษา LINE กำลังเริ่มทำงาน...")
    print(f"📡 监听地址 / ที่อยู่เซิร์ฟเวอร์: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"🤖 当前模型 / โมเดล Gemini: {config.GEMINI_MODEL} (备用 / สำรอง: {config.GEMINI_FALLBACK_MODEL})")
    print("=" * 60)
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT)
