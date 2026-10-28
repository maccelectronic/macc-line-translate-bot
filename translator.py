"""
翻译核心模块 / โมดูลแปลภาษาหลัก (Translator Module)
负责语系识别、群聊噪声过滤、调用 Google Gemini 3.8 Flash 实现简体中文 ⇄ 泰语互译
ทำหน้าที่ตรวจจับภาษา, กรองคำสั่งในกลุ่ม, และแปลภาษา จีนตัวย่อ ⇄ ไทย ผ่าน Gemini 3.8 Flash
"""
import re
from google import genai
from google.genai import types
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


def build_system_instruction(gender: str = 'neutral') -> str:
    """
    根据发言者性别动态构造针对性的系统提示词 / สร้าง System Instruction ตามเพศของผู้พูด
    :param gender: 'male', 'female', 或 'neutral'
    """
    if gender == 'male':
        gender_directive = (
            "SPEAKER GENDER DIRECTIVE: The speaker is MALE. When translating into Thai, "
            "use the polite male ending particle 'ครับ' and male first-person pronoun 'ผม' where appropriate. "
            "NEVER use female particles (ค่ะ/คะ) or slash choices (such as 'ครับ/ค่ะ', 'ผม/ฉัน')."
        )
    elif gender == 'female':
        gender_directive = (
            "SPEAKER GENDER DIRECTIVE: The speaker is FEMALE. When translating into Thai, "
            "use the polite female ending particle 'ค่ะ' (or 'คะ' for questions) and female pronoun "
            "'ดิฉัน' or 'ฉัน' where appropriate. NEVER use male particles (ครับ) or slash choices (such as 'ครับ/ค่ะ', 'ผม/ฉัน')."
        )
    else:
        gender_directive = (
            "SPEAKER GENDER DIRECTIVE: The speaker gender is UNSPECIFIED. When translating into Thai, "
            "use polite business Thai, prefer omitting first-person pronouns or use 'ทางเรา' where natural, "
            "and use standard polite particle 'ครับ'. NEVER use slash choices (such as 'ครับ/ค่ะ', 'ผม/ฉัน')."
        )

    return f"""You are a strict, automated, direct translation engine for real-time chat between Simplified Chinese (简体中文) and Thai (ภาษาไทย).

CRITICAL DIRECTIVES:
1. Output ONLY the raw translated text. Absolutely NOTHING else.
2. Strictly NO explanations, NO notes, NO conversational filler, NO pronunciation guides, NO vocabulary breakdowns.
3. Strictly NO thoughts, NO internal monologue, NO meta-commentary (e.g., do NOT output "*Wait...", "Let's...", "Actually...", "Translation:").
4. Strictly NO alternative options or slash choices (such as 'ครับ/ค่ะ', 'ผม/ฉัน'). Select the single most natural, professional, polite wording directly.
5. {gender_directive}
6. If target is Chinese, strictly use Simplified Chinese (简体中文).
7. Do NOT wrap the translation in quotation marks unless the original source text was enclosed in quotation marks.
"""


def clean_translation(result: str, original: str) -> str:
    """
    清洗模型输出，杜绝任何解释性文字、思考残留或多余引号泄露到群聊中
    """
    if not result:
        return ""
    lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
    if not lines:
        return ""

    content_lines = []
    for l in lines:
        if l.startswith(('---', '===', '___')):
            break
        lower = l.lower()
        if any(lower.startswith(p) for p in (
            '*wait', 'wait,', 'note:', 'notes:', 'explanation:', 'here is', 'translation:',
            'vocabulary', 'breakdown:', 'role:', 'task:', "let's", 'actually,', 'since gender',
            'better neutral', 'or neutral:', 'or:'
        )):
            continue
        content_lines.append(l)

    if not content_lines:
        content_lines = [lines[0]]

    text = "\n".join(content_lines).strip()

    orig = original.strip()
    orig_quoted = (
        (orig.startswith('"') and orig.endswith('"')) or
        (orig.startswith('“') and orig.endswith('”')) or
        (orig.startswith("'") and orig.endswith("'"))
    )
    if not orig_quoted:
        if (text.startswith('"') and text.endswith('"')) or (text.startswith('“') and text.endswith('”')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()

    return text


class GeminiTranslator:
    """
    Gemini 翻译器封装类 / คลาสจัดการการแปลภาษาด้วย Gemini
    支持主模型与备用模型自动故障转移 / รองรับการสลับโมเดลสำรองอัตโนมัติเมื่อเกิดข้อผิดพลาด
    """

    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = config.GEMINI_MODEL
        self.fallback_model = config.GEMINI_FALLBACK_MODEL
        
        # 预设不同性别配置，避免每次调用重复构建
        self.configs = {
            g: types.GenerateContentConfig(
                system_instruction=build_system_instruction(g),
                temperature=0.0,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )
            for g in ('male', 'female', 'neutral')
        }
        self.fallback_configs = {
            g: types.GenerateContentConfig(
                system_instruction=build_system_instruction(g),
                temperature=0.0
            )
            for g in ('male', 'female', 'neutral')
        }

    def translate(self, text: str, target_lang: str, gender: str = 'neutral') -> str | None:
        """
        调用 Gemini API 进行高质量翻译 / เรียกใช้ Gemini API เพื่อแปลภาษา
        :param text: 待翻译原文 / ข้อความต้นฉบับ
        :param target_lang: 目标语言 / ภาษาปลายทาง (เช่น 'Simplified Chinese (简体中文)', 'Thai (ภาษาไทย)')
        :param gender: 发言者性别 ('male', 'female', 'neutral')
        :return: 翻译结果字符串，失败则返回 None / ข้อความที่แปลแล้ว หรือ None หากล้มเหลว
        """
        if gender not in self.configs:
            gender = 'neutral'
        gen_config = self.configs[gender]
        fallback_gen_config = self.fallback_configs[gender]

        prompt = f"Translate to {target_lang}:\n{text}"
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=gen_config
            )
            if response.text:
                return clean_translation(response.text, text)
            return None
        except Exception as e:
            print(f"[Gemini 错误 / ข้อผิดพลาด] 主模型 / โมเดลหลัก ({self.model}) 失败: {e}")
            if "404" in str(e) or "not found" in str(e).lower() or "quota" in str(e).lower():
                print(f"[Gemini 切换 / สลับโมเดล] 自动启用备用模型 / เปลี่ยนเป็นโมเดลสำรอง: {self.fallback_model}...")
                try:
                    response = self.client.models.generate_content(
                        model=self.fallback_model, contents=prompt, config=fallback_gen_config
                    )
                    if response.text:
                        return clean_translation(response.text, text)
                    return None
                except Exception as fallback_e:
                    print(f"[Gemini 备用模型错误 / ข้อผิดพลาดโมเดลสำรอง] {fallback_e}")
            return None


# 全局翻译器单例 / อินสแตนซ์ตัวแปลภาษาแบบโกลบอล
translator = GeminiTranslator()


def translate_message(text: str, gender: str = 'neutral') -> str | None:
    """
    群聊消息处理流程 / ขั้นตอนการประมวลผลข้อความในกลุ่ม:
    1. 忽略指令与链接 / กรองและข้ามคำสั่งและลิงก์ URL
    2. 自动识别泰语/中文并执行双向互译 / ตรวจจับภาษาไทย/จีน และแปลสองทิศทาง
    3. 添加国旗标签并返回 / ใส่แท็กธงชาติและส่งกลับผลลัพธ์
    :param text: 消息原文
    :param gender: 发言者性别 ('male', 'female', 'neutral')
    """
    if not text:
        return None

    # 1. 忽略群聊常见指令 (/, !, #) 与网址 (http://, https://) / ข้ามคำสั่งและลิงก์
    if text.startswith(('/', '!', '#', 'http://', 'https://')):
        return None

    # 2. 泰语 -> 简体中文 / ภาษาไทย -> ภาษาจีนตัวย่อ
    if is_thai(text):
        translated = translator.translate(text, "Simplified Chinese (简体中文)", gender=gender)
        if translated:
            return f"🇹🇭 -> 🇨🇳 :\n{translated}"

    # 3. 中文 -> 泰语 / ภาษาจีน -> ภาษาไทย
    elif is_chinese(text):
        translated = translator.translate(text, "Thai (ภาษาไทย)", gender=gender)
        if translated:
            return f"🇨🇳 -> 🇹🇭 :\n{translated}"

    return None
