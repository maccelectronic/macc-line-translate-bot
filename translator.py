"""
翻译核心模块 / โมดูลแปลภาษาหลัก (Translator Module)
负责语系识别、群聊噪声过滤、调用 Google Gemini 3.7 Flash 实现简体中文 ⇄ 泰语互译
ทำหน้าที่ตรวจจับภาษา, กรองคำสั่งในกลุ่ม, และแปลภาษา จีนตัวย่อ ⇄ ไทย ผ่าน Gemini 3.7 Flash
"""
import re
from google import genai
import config


def is_thai(text: str) -> bool:
    """
    判断文字是否包含泰文字符 / ตรวจสอบว่ามีตัวอักษรภาษาไทยหรือไม่
    Unicode range: U+0E00 - U+0E7F
    """
    return bool(re.search(r'[\u0e00-\u0e7f]', text))


def is_chinese(text: str) -> bool:
    """
    判断文字是否包含中文字符 / ตรวจสอบว่ามีตัวอักษรภาษาจีนหรือไม่
    Unicode range: U+4E00 - U+9FA5
    """
    return bool(re.search(r'[\u4e00-\u9fa5]', text))


class GeminiTranslator:
    """
    Gemini 翻译器封装类 / คลาสจัดการการแปลภาษาด้วย Gemini
    支持主模型与备用模型自动故障转移 / รองรับการสลับโมเดลสำรองอัตโนมัติเมื่อเกิดข้อผิดพลาด
    """

    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = config.GEMINI_MODEL
        self.fallback_model = config.GEMINI_FALLBACK_MODEL

    def translate(self, text: str, target_lang: str) -> str | None:
        """
        调用 Gemini API 进行高质量翻译 / เรียกใช้ Gemini API เพื่อแปลภาษา
        :param text: 待翻译原文 / ข้อความต้นฉบับ
        :param target_lang: 目标语言 / ภาษาปลายทาง (เช่น 'Simplified Chinese (简体中文)', 'Thai (ภาษาไทย)')
        :return: 翻译结果字符串，失败则返回 None / ข้อความที่แปลแล้ว หรือ None หากล้มเหลว
        """
        prompt = f"""
Role: Professional Translator specializing in Simplified Chinese (简体中文) and Thai (ภาษาไทย).
Task: Translate the following text into {target_lang}.

Constraints:
1. Output ONLY the translated text without explanations, conversational filler, or notes.
2. When translating into Chinese, strictly output Simplified Chinese (简体中文).
3. Accurately maintain the original meaning, tone, emotion, and context.
4. Do NOT include quotation marks around the output unless present in the original text.

Text to translate:
"{text}"
"""
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt
            )
            if response.text:
                result = response.text.strip()
                if (result.startswith('"') and result.endswith('"')) or (result.startswith('“') and result.endswith('”')):
                    result = result[1:-1].strip()
                return result
            return None
        except Exception as e:
            print(f"[Gemini 错误 / ข้อผิดพลาด] 主模型 / โมเดลหลัก ({self.model}) 失败: {e}")
            if "404" in str(e) or "not found" in str(e).lower() or "quota" in str(e).lower():
                print(f"[Gemini 切换 / สลับโมเดล] 自动启用备用模型 / เปลี่ยนเป็นโมเดลสำรอง: {self.fallback_model}...")
                try:
                    response = self.client.models.generate_content(
                        model=self.fallback_model, contents=prompt
                    )
                    if response.text:
                        result = response.text.strip()
                        if (result.startswith('"') and result.endswith('"')) or (result.startswith('“') and result.endswith('”')):
                            result = result[1:-1].strip()
                        return result
                    return None
                except Exception as fallback_e:
                    print(f"[Gemini 备用模型错误 / ข้อผิดพลาดโมเดลสำรอง] {fallback_e}")
            return None


# 全局翻译器单例 / อินสแตนซ์ตัวแปลภาษาแบบโกลบอล
translator = GeminiTranslator()


def translate_message(text: str) -> str | None:
    """
    群聊消息处理流程 / ขั้นตอนการประมวลผลข้อความในกลุ่ม:
    1. 忽略指令与链接 / กรองและข้ามคำสั่งและลิงก์ URL
    2. 自动识别泰语/中文并执行双向互译 / ตรวจจับภาษาไทย/จีน และแปลสองทิศทาง
    3. 添加国旗标签并返回 / ใส่แท็กธงชาติและส่งกลับผลลัพธ์
    """
    if not text:
        return None

    # 1. 忽略群聊常见指令 (/, !, #) 与网址 (http://, https://) / ข้ามคำสั่งและลิงก์
    if text.startswith(('/', '!', '#', 'http://', 'https://')):
        return None

    # 2. 泰语 -> 简体中文 / ภาษาไทย -> ภาษาจีนตัวย่อ
    if is_thai(text):
        translated = translator.translate(text, "Simplified Chinese (简体中文)")
        if translated:
            return f"🇹🇭 -> 🇨🇳 :\n{translated}"

    # 3. 中文 -> 泰语 / ภาษาจีน -> ภาษาไทย
    elif is_chinese(text):
        translated = translator.translate(text, "Thai (ภาษาไทย)")
        if translated:
            return f"🇨🇳 -> 🇹🇭 :\n{translated}"

    return None
