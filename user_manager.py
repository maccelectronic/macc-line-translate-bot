"""
用户性别管理与 AI 画像识别模块 / โมดูลจัดการเพศของผู้ใช้ (User Manager Module)
负责用户性别持久化存储（SQLite）及基于昵称/头像的 Gemini 多模态识别
"""
import os
import json
import sqlite3
import threading
from typing import Optional, Tuple
import requests
from google import genai
from google.genai import types

import config

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "user_profiles.db")

_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """获取 SQLite 数据库连接并自动建表"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                picture_url TEXT,
                gender TEXT,          -- 'male', 'female', 'neutral'
                set_by TEXT,          -- 'manual', 'ai'
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    return conn


# 全局数据库连接单例
_db_conn = get_db_connection()


def get_user_gender(user_id: str) -> Tuple[str, str]:
    """
    查询用户性别记录
    :param user_id: LINE 用户 ID
    :return: (gender, set_by) 例如 ('male', 'manual'), ('female', 'ai'), ('neutral', 'default')
    """
    if not user_id:
        return 'neutral', 'default'

    with _lock:
        cursor = _db_conn.cursor()
        cursor.execute("SELECT gender, set_by FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row["gender"], row["set_by"]
        return 'neutral', 'default'


def set_user_gender_manual(user_id: str, gender: str, display_name: Optional[str] = None) -> None:
    """
    用户主动发送指令设置性别（最高优先级）
    :param user_id: LINE 用户 ID
    :param gender: 'male' 或 'female'
    :param display_name: 用户昵称（可选）
    """
    if not user_id or gender not in ('male', 'female', 'neutral'):
        return

    with _lock:
        cursor = _db_conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, display_name, gender, set_by, updated_at)
            VALUES (?, ?, ?, 'manual', CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                gender = excluded.gender,
                set_by = 'manual',
                display_name = COALESCE(excluded.display_name, users.display_name),
                updated_at = CURRENT_TIMESTAMP;
        """, (user_id, display_name, gender))
        _db_conn.commit()


def reset_user_gender(user_id: str) -> None:
    """重置用户性别设置，恢复由 AI 自动推断"""
    if not user_id:
        return
    with _lock:
        cursor = _db_conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        _db_conn.commit()


def infer_and_save_gender(
    user_id: str,
    display_name: Optional[str] = None,
    picture_url: Optional[str] = None,
    client: Optional[genai.Client] = None
) -> str:
    """
    使用 Gemini 结合用户昵称与头像多模态推断性别，并持久化缓存
    :param user_id: LINE 用户 ID
    :param display_name: 用户昵称
    :param picture_url: 头像 URL
    :param client: 可选的 genai.Client 实例
    :return: 推断出的性别 ('male', 'female', 或 'neutral')
    """
    if not user_id:
        return 'neutral'

    # 1. 检查本地数据库是否已有记录（尤其是 manual 手动设置，绝对不能覆盖）
    current_gender, set_by = get_user_gender(user_id)
    if set_by == 'manual':
        return current_gender

    # 2. 如果昵称和头像都为空，无法推断，返回中性
    if not display_name and not picture_url:
        return 'neutral'

    # 3. 构建 Gemini 多模态推断请求
    if client is None:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = f"""You are a cultural and demographic AI assistant.
Analyze the following LINE user's profile details to determine whether the person is likely male or female.

User details:
- Display name: {display_name or 'Not provided'}

Instructions:
1. Examine the display name for gendered indicators (e.g. names like John, Somchai, Nongnuch, Anna, 张伟, 娜娜, Mr., Ms., titles, emojis like 👨, 👧).
2. If an avatar photo is provided, examine visual gender cues (face, hair, clothing, presentation).
3. If the avatar is scenery, anime, a pet, an object, a corporate logo, or gender cannot be determined with certainty, choose 'unknown'.
4. Return ONLY valid JSON:
{{"gender": "male" | "female" | "unknown", "confidence": float between 0.0 and 1.0}}
"""

    contents = []

    # 尝试下载头像作为图像输入
    if picture_url:
        try:
            resp = requests.get(picture_url, timeout=3)
            if resp.status_code == 200 and resp.content:
                mime_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
                contents.append(types.Part.from_bytes(data=resp.content, mime_type=mime_type))
        except Exception as img_err:
            print(f"[头像下载异常 / ดาวน์โหลดรูปไม่สำเร็จ] {img_err}")

    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        if response.text:
            data = json.loads(response.text.strip())
            gender = data.get("gender", "unknown").lower()
            confidence = float(data.get("confidence", 0.0))

            final_gender = 'neutral'
            if gender in ('male', 'female') and confidence >= 0.75:
                final_gender = gender

            # 写入本地数据库，后续该用户发言可秒查
            with _lock:
                cursor = _db_conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, display_name, picture_url, gender, set_by, updated_at)
                    VALUES (?, ?, ?, ?, 'ai', CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        display_name = COALESCE(excluded.display_name, users.display_name),
                        picture_url = COALESCE(excluded.picture_url, users.picture_url),
                        gender = excluded.gender,
                        set_by = 'ai',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE users.set_by != 'manual';
                """, (user_id, display_name, picture_url, final_gender))
                _db_conn.commit()

            print(f"[AI 性别推断] 用户: {display_name} -> {final_gender} (置信度: {confidence:.2f})")
            return final_gender
    except Exception as e:
        print(f"[AI 性别推断失败 / การอนุมานเพศล้มเหลว] {e}")

    return 'neutral'
