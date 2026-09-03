"""
主服务器模块 / โมดูลเซิร์ฟเวอร์หลัก (Main Server)
基于 Flask 提供 LINE Webhook API 端点，接收群聊/私聊消息并自动翻译回复
รันเซิร์ฟเวอร์ Flask รับ Webhook จาก LINE แปลภาษาอัตโนมัติและตอบกลับในกลุ่ม/แชท
"""
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


@app.route("/line/callback", methods=['POST'])
def callback():
    """
    LINE Webhook 回调入口，验证数字签名并分发事件
    จุดรับ Webhook จาก LINE ตรวจสอบลายเซ็นดิจิทัลและส่งต่อเหตุการณ์
    """
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    if signature is None:
        return 'Missing Signature', 400

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("[LINE 错误 / ข้อผิดพลาด] 签名验证失败 / ตรวจสอบลายเซ็นไม่ผ่าน (Invalid Signature)")
        abort(400)
    except Exception as e:
        print(f"[Webhook 异常 / ข้อผิดพลาด Webhook] {e}")
        abort(500)

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """
    处理收到的文本消息（支持群聊与私聊）
    ประมวลผลข้อความตัวอักษรที่ได้รับ (รองรับทั้งกลุ่มและแชทส่วนตัว)
    """
    msg = event.message.text.strip()
    reply_text = translate_message(msg)

    if reply_text:
        source_type = event.source.type if hasattr(event, 'source') and hasattr(event.source, 'type') else 'unknown'
        print(f"[消息处理 / ประมวลผลข้อความ] 来源 / แหล่งที่มา: {source_type}\n{reply_text}")
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_text)]
                    )
                )
        except Exception as e:
            print(f"[LINE 回复失败 / ส่งข้อความตอบกลับไม่สำเร็จ] {e}")


if __name__ == "__main__":
    # 启动前自检 / ตรวจสอบความถูกต้องก่อนเริ่มระบบ
    config.validate_config()
    print("=" * 60)
    print("🚀 LINE 翻译机器人启动中... / บอตแปลภาษา LINE กำลังเริ่มทำงาน...")
    print(f"📡 监听地址 / ที่อยู่เซิร์ฟเวอร์: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"🤖 当前模型 / โมเดล Gemini: {config.GEMINI_MODEL} (备用 / สำรอง: {config.GEMINI_FALLBACK_MODEL})")
    print("=" * 60)
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT)
