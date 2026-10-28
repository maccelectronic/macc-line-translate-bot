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

from typing import Optional, Tuple

import config
from translator import translate_message, is_thai, is_chinese
import user_manager

# 用户性别配置指令集 / ชุดคำสั่งตั้งค่าเพศ
MALE_COMMANDS = {'我是男生', '我是男', '我是男的', '/male', 'ผมเป็นผู้ชาย', '/gender male'}
FEMALE_COMMANDS = {'我是女生', '我是女', '我是女的', '/female', 'ฉันเป็นผู้หญิง', 'ดิฉันเป็นผู้หญิง', '/gender female'}
RESET_COMMANDS = {'重置性别', '清除性别', '/gender reset', 'รีเซ็ตเพศ'}
QUERY_COMMANDS = {'我的性别', '/gender', 'เพศของฉัน'}


def get_user_profile_safe(line_bot_api: MessagingApi, event) -> Tuple[Optional[str], Optional[str]]:
    """
    安全获取用户昵称与头像 URL（支持群聊、聊天室、私聊）
    ดึงข้อมูลโปรไฟล์ผู้ใช้ (ชื่อและรูปภาพ) อย่างปลอดภัย
    """
    try:
        source = getattr(event, 'source', None)
        if not source:
            return None, None
        source_type = getattr(source, 'type', None)
        user_id = getattr(source, 'user_id', None)
        if not user_id:
            return None, None

        if source_type == 'group':
            group_id = getattr(source, 'group_id', None)
            if group_id:
                profile = line_bot_api.get_group_member_profile(group_id, user_id)
                return getattr(profile, 'display_name', None), getattr(profile, 'picture_url', None)
        elif source_type == 'room':
            room_id = getattr(source, 'room_id', None)
            if room_id:
                profile = line_bot_api.get_room_member_profile(room_id, user_id)
                return getattr(profile, 'display_name', None), getattr(profile, 'picture_url', None)

        profile = line_bot_api.get_profile(user_id)
        return getattr(profile, 'display_name', None), getattr(profile, 'picture_url', None)
    except Exception as e:
        print(f"[获取 LINE 用户资料失败 / ดึงข้อมูลโปรไฟล์ไม่สำเร็จ] {e}")
        return None, None

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
    user_id = getattr(event.source, 'user_id', None) if hasattr(event, 'source') else None

    norm_msg = msg.lower()

    # 1. 检查是否为性别设置/查询指令
    is_gender_cmd = (
        norm_msg in MALE_COMMANDS or
        norm_msg in FEMALE_COMMANDS or
        norm_msg in RESET_COMMANDS or
        norm_msg in QUERY_COMMANDS
    )

    if is_gender_cmd:
        if not user_id:
            reply_text = "无法识别您的用户 ID，暂无法设置性别。\nไม่สามารถระบุตัวตนของคุณได้"
        else:
            try:
                with ApiClient(configuration) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    display_name, _ = get_user_profile_safe(line_bot_api, event)

                    if norm_msg in MALE_COMMANDS:
                        user_manager.set_user_gender_manual(user_id, 'male', display_name=display_name)
                        reply_text = (
                            "🇹🇭/🇨🇳 :\n"
                            "✅ 已记录您的性别为【男士】👨\n"
                            "后续翻译将为您适配男性礼貌语气词与人称代词（ครับ / ผม）\n"
                            "--------------------\n"
                            "บันทึกเพศของคุณเป็น [ผู้ชาย] เรียบร้อยแล้วครับ"
                        )
                    elif norm_msg in FEMALE_COMMANDS:
                        user_manager.set_user_gender_manual(user_id, 'female', display_name=display_name)
                        reply_text = (
                            "🇹🇭/🇨🇳 :\n"
                            "✅ 已记录您的性别为【女士】👩\n"
                            "后续翻译将为您适配女性礼貌语气词与人称代词（ค่ะ / ดิฉัน / ฉัน）\n"
                            "--------------------\n"
                            "บันทึกเพศของคุณเป็น [ผู้หญิง] เรียบร้อยแล้วค่ะ"
                        )
                    elif norm_msg in RESET_COMMANDS:
                        user_manager.reset_user_gender(user_id)
                        reply_text = (
                            "🇹🇭/🇨🇳 :\n"
                            "🔄 已重置性别设置，后续将恢复通过昵称/头像自动识别\n"
                            "--------------------\n"
                            "รีเซ็ตการตั้งค่าเพศเรียบร้อยแล้วครับ/ค่ะ"
                        )
                    elif norm_msg in QUERY_COMMANDS:
                        gender, set_by = user_manager.get_user_gender(user_id)
                        gender_cn = {"male": "男士 👨", "female": "女士 👩", "neutral": "未设定/中性 👤"}.get(gender, "未设定 👤")
                        gender_th = {"male": "ผู้ชาย 👨", "female": "ผู้หญิง 👩", "neutral": "ไม่ระบุ 👤"}.get(gender, "ไม่ระบุ 👤")
                        source_cn = "手动设置" if set_by == "manual" else ("AI 自动识别" if set_by == "ai" else "系统默认")
                        source_th = "ตั้งค่าด้วยตนเอง" if set_by == "manual" else ("วิเคราะห์อัตโนมัติด้วย AI" if set_by == "ai" else "ค่าเริ่มต้น")
                        reply_text = (
                            f"🇹🇭/🇨🇳 :\n"
                            f"ℹ️ 您当前登记的性别为：【{gender_cn}】（来源：{source_cn}）\n"
                            f"如需更改可发送「我是男生」或「我是女生」，发送「重置性别」可恢复自动识别。\n"
                            f"--------------------\n"
                            f"ข้อมูลเพศปัจจุบัน: [{gender_th}] ({source_th})"
                        )

                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_text)]
                        )
                    )
                print(f"[性别指令响应成功] 来源: {source_type} (用户: {user_id[:8]}... | 指令: {msg})")
            except Exception as e:
                print(f"[性别指令处理失败] {e}")
        return

    # 2. 普通聊天消息前置过滤：忽略群聊常见指令 (/, !, #) 与网址，且只翻译中泰文本
    if msg.startswith(('/', '!', '#', 'http://', 'https://')) or (not is_thai(msg) and not is_chinese(msg)):
        print(f"[忽略消息 / ข้ามข้อความ] 来源: {source_type} | 原文无需翻译: {msg}")
        return

    # 3. 获取用户性别（优先查本地 SQLite，若未记录则触发 AI 自动识别并入库）
    user_gender = 'neutral'
    if user_id:
        gender, set_by = user_manager.get_user_gender(user_id)
        if set_by != 'default':
            user_gender = gender
        else:
            # 首次发言：获取用户昵称与头像，调用 Gemini 3.8 Flash 多模态自动推断性别
            try:
                with ApiClient(configuration) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    display_name, picture_url = get_user_profile_safe(line_bot_api, event)
                user_gender = user_manager.infer_and_save_gender(
                    user_id=user_id,
                    display_name=display_name,
                    picture_url=picture_url
                )
            except Exception as e:
                print(f"[用户画像推断异常 / ข้อผิดพลาดอนุมานโปรไฟล์] {e}")
                user_gender = 'neutral'

    # 4. 执行中泰互译（注入性别敬语指令）
    reply_text = translate_message(msg, gender=user_gender)

    if reply_text:
        print(f"[消息处理 / ประมวลผลข้อความ] 来源: {source_type} (用户: {user_id[:8] if user_id else 'unknown'}... | 性别: {user_gender})\n原文: {msg}\n{reply_text}")
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
