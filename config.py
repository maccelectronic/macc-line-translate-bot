"""
配置模块 / โมดูลการตั้งค่า (Configuration Module)
负责加载环境变量与全局配置 / จัดการโหลดตัวแปรสภาพแวดล้อมและการตั้งค่าส่วนกลาง
"""
import os
from dotenv import load_dotenv

# 加载 .env 环境变量 / โหลดตัวแปรสภาพแวดล้อมจากไฟล์ .env
load_dotenv()

# LINE 机器人配置 / การตั้งค่า LINE Bot
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# Gemini AI 配置 / การตั้งค่า Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")

# 服务器配置 / การตั้งค่าเซิร์ฟเวอร์
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))


def validate_config():
    """
    验证必要环境变量是否存在 / ตรวจสอบว่ามีตัวแปรสภาพแวดล้อมที่จำเป็นครบถ้วนหรือไม่
    """
    missing = []
    if not LINE_CHANNEL_ACCESS_TOKEN:
        missing.append("LINE_CHANNEL_ACCESS_TOKEN")
    if not LINE_CHANNEL_SECRET:
        missing.append("LINE_CHANNEL_SECRET")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if missing:
        print(f"[警告 / คำเตือน] 缺少关键环境变量 / ขาดตัวแปรสำคัญ: {', '.join(missing)}")
