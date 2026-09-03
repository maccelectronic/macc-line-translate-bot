# 🌐 บอตแปลภาษาแบบเรียลไทม์ จีนตัวย่อ ⇄ ไทย บน LINE (LINE Translate Bot)

[🇹🇭 ภาษาไทย (README_TH.md)](./README_TH.md) | [🇨🇳 简体中文 (README.md)](./README.md)

บอตแปลภาษาอัจฉริยะบน LINE พัฒนาด้วย **Flask** และ **Google Gemini 3.7 Flash** ออกแบบและปรับแต่งมาเป็นพิเศษสำหรับ **กลุ่ม LINE (Group Chat)** และการแชทส่วนตัว สามารถตรวจจับภาษาไทยและภาษาจีนตัวย่อได้อัตโนมัติ พร้อมแปลสองทิศทางได้อย่างแม่นยำและเป็นธรรมชาติ

---

## 📑 สารบัญ (Table of Contents)
- [โครงสร้างระบบและขั้นตอนการทำงาน (Architecture & Workflow)](#-โครงสร้างระบบและขั้นตอนการทำงาน-architecture--workflow)
- [โครงสร้างไดเรกทอรีโปรเจกต์ (Project Structure)](#-โครงสร้างไดเรกทอรีโปรเจกต์-project-structure)
- [คำอธิบายโมดูลหลัก (Core Modules)](#-คำอธิบายโมดูลหลัก-core-modules)
- [การตั้งค่าตัวแปรสภาพแวดล้อม (.env)](#-การตั้งค่าตัวแปรสภาพแวดล้อม-env)
- [คู่มือการติดตั้งและเริ่มใช้งาน (Installation & Setup)](#-คู่มือการติดตั้งและเริ่มใช้งาน-installation--setup)
- [การตั้งค่าสำคัญสำหรับกลุ่ม LINE (LINE Group Chat Settings)](#-การตั้งค่าสำคัญสำหรับกลุ่ม-line-line-group-chat-settings)
- [คำสั่งสำหรับทดสอบและบำรุงรักษา (Maintenance Commands)](#-คำสั่งสำหรับทดสอบและบำรุงรักษา-maintenance-commands)

---

## 🏗️ โครงสร้างระบบและขั้นตอนการทำงาน (Architecture & Workflow)

```mermaid
flowchart TD
    A[👤 สมาชิกในกลุ่ม LINE / แชทส่วนตัว] -->|ส่งข้อความ| B[เซิร์ฟเวอร์ LINE]
    B -->|Webhook POST /line/callback| C["Flask แอปพลิเคชัน (main.py)"]
    C -->|ตรวจสอบความถูกต้อง X-Line-Signature| D{ลายเซ็นถูกต้องหรือไม่?}
    D -- ไม่ถูกต้อง --> E[ส่งกลับ 400 Bad Request]
    D -- ถูกต้อง --> F["โมดูลประมวลผลการแปล (translator.py)"]
    
    F -->|กรองคำสั่งและลิงก์ / ! # http| G{จำเป็นต้องแปลหรือไม่?}
    G -- ไม่ (คำสั่ง/ภาษาอังกฤษ/ลิงก์) --> H[ข้ามข้อความ ไม่รบกวนกลุ่ม]
    G -- ใช่ (มีภาษาจีนหรือไทย) --> I["เรียกใช้งาน Google Gemini API"]
    
    I -->|โมเดลหลัก: gemini-3.7-flash| J{สถานะการเรียก API}
    J -- สำเร็จ --> K[รับข้อความที่แปลแล้ว]
    J -- ล้มเหลว/โควตาเต็ม --> L["สลับไปยังโมเดลสำรองอัตโนมัติ (gemini-3.1-flash-lite)"] --> K
    
    K --> M[ใส่แท็กธงชาติ 🇹🇭 / 🇨🇳]
    M -->|ตอบกลับผ่าน LINE Messaging API| B
    B -->|แสดงผลการแปลในกลุ่ม LINE| A
```

---

## 📂 โครงสร้างไดเรกทอรีโปรเจกต์ (Project Structure)

```text
translate_bot/
├── config.py           # ⚙️ โหลดการตั้งค่าและตัวแปรสภาพแวดล้อม (พร้อมระบบตรวจสอบ)
├── main.py             # 🚀 จุดเริ่มต้นของเซิร์ฟเวอร์ Webhook (Flask + LINE SDK v3)
├── translator.py       # 🧠 ตรวจจับภาษา, กรองคำสั่ง, และแปลภาษาผ่าน Gemini 3.7 Flash
├── .env                # 🔑 ไฟล์เก็บคีย์และข้อมูลสำคัญ (ห้ามอัปโหลดขึ้น Git)
├── .env.example        # 📝 ไฟล์ตัวอย่างการตั้งค่าตัวแปรสภาพแวดล้อม
├── requirements.txt    # 📦 รายการแพ็กเกจ Python ที่จำเป็น
├── .gitignore          # 🚫 รายการไฟล์ที่ Git จะเพิกเฉย
├── README.md           # 📖 คู่มือการใช้งานภาษาจีน (简体中文)
└── README_TH.md        # 📖 คู่มือการใช้งานและโครงสร้างระบบภาษาไทย (ภาษาไทย)
```

---

## 🧩 คำอธิบายโมดูลหลัก (Core Modules)

| ชื่อไฟล์ | หน้าที่และความรับผิดชอบ |
| :--- | :--- |
| **`main.py`** | 1. รันเซิร์ฟเวอร์ Flask รับการเชื่อมต่อ Webhook ที่เส้นทาง `/line/callback`<br>2. ตรวจสอบลายเซ็นดิจิทัลของ LINE (`X-Line-Signature`)<br>3. รับเหตุการณ์ข้อความ (`MessageEvent`) เรียกฟังก์ชันแปล และตอบกลับผ่าน `reply_message` |
| **`translator.py`** | 1. **ตรวจจับภาษา**: ใช้ Regular Expression ตรวจหาตัวอักษรไทย (`\u0e00-\u0e7f`) และจีน (`\u4e00-\u9fa5`)<br>2. **ลดสัญญาณรบกวนในกลุ่ม**: กรองและข้ามข้อความที่ขึ้นต้นด้วย `/`, `!`, `#` และลิงก์ URL อัตโนมัติ<br>3. **AI แปลภาษา**: คลาส `GeminiTranslator` ใช้โมเดล `gemini-3.7-flash` แปลระหว่างจีนตัวย่อและไทยอย่างแม่นยำ พร้อมระบบ Fallback สลับโมเดลสำรองเมื่อเกิดข้อผิดพลาด |
| **`config.py`** | 1. รวบรวมการตั้งค่า Token, Secret, API Key, ชื่อโมเดล และหมายเลขพอร์ต<br>2. ฟังก์ชัน `validate_config()` ตรวจสอบว่าคีย์สำคัญครบถ้วนหรือไม่ก่อนเริ่มทำงาน |

---

## 🔑 การตั้งค่าตัวแปรสภาพแวดล้อม (.env)

คัดลอกไฟล์ `.env.example` ไปเป็น `.env` แล้วระบุคีย์ของคุณ:

```ini
# ==========================================
# การตั้งค่า LINE Bot / LINE Bot Configuration
# ==========================================
# รับจาก LINE Developers Console -> Messaging API -> Channel access token
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here

# รับจาก LINE Developers Console -> Basic settings -> Channel secret
LINE_CHANNEL_SECRET=your_line_channel_secret_here

# ==========================================
# การตั้งค่า Gemini AI / Gemini AI Configuration
# ==========================================
# รับ API Key จาก Google AI Studio (https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# โมเดลหลักสำหรับการแปล (แนะนำ gemini-3.7-flash)
GEMINI_MODEL=gemini-3.7-flash

# โมเดลสำรอง (จะทำงานอัตโนมัติหากโมเดลหลักมีปัญหา)
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite

# ==========================================
# การตั้งค่าเซิร์ฟเวอร์ / Server Configuration
# ==========================================
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

---

## 🚀 คู่มือการติดตั้งและเริ่มใช้งาน (Installation & Setup)

### 1. สร้าง Virtual Environment และติดตั้งแพ็กเกจ
```bash
cd /home/ubuntu/Desktop/translate_bot

# สร้างสภาพแวดล้อมเสมือนของ Python (หากยังไม่มี)
python3 -m venv venv

# ติดตั้งไลบรารีที่จำเป็น
./venv/bin/pip install -r requirements.txt
```

### 2. รันเพื่อทดสอบเบื้องต้น
```bash
./venv/bin/python main.py
```

### 3. รันเป็น Background Service ด้วย nohup
```bash
# รันเบื้องหลังและบันทึก Log ลงไฟล์ bot.log
nohup ./venv/bin/python main.py > bot.log 2>&1 &

# ดู Log แบบเรียลไทม์
tail -f bot.log

# ตรวจสอบสถานะการทำงานของ Process
ps aux | grep main.py
```

---

## 📌 การตั้งค่าสำคัญสำหรับกลุ่ม LINE (LINE Group Chat Settings)

เพื่อให้บอตทำงานในกลุ่ม LINE ได้อย่างราบรื่น กรุณาตรวจสอบการตั้งค่า 3 จุดใน [LINE Official Account Manager](https://manager.line.biz/):

1. **อนุญาตให้บอตเข้ากลุ่ม (Allow bot to join group chats)**:
   - ไปที่ **ตั้งค่า (Settings)** -> **ตั้งค่าบัญชี (Account settings)** -> เปิดใช้งาน **「อนุญาตให้เข้าร่วมกลุ่มหรือการสนทนาหลายคน (Allow bot to join group chats)」**
2. **ปิดข้อความตอบกลับอัตโนมัติ (Auto-reply messages)**:
   - ไปที่ **ตั้งค่าการตอบกลับ (Response settings)** -> เลือกโหมดการตอบกลับเป็น **「บอต (Bot)」** -> ปิด **「ข้อความตอบกลับอัตโนมัติ (Auto-reply messages) ให้เป็น OFF」** เพื่อป้องกันข้อความตอบกลับอัตโนมัติรบกวนสมาชิกในกลุ่ม
3. **เปิดใช้งาน Webhook**:
   - ในหน้า LINE Developers Console -> Messaging API ให้เปิด **「Use webhook」** และกรอก URL ที่เข้าถึงได้จากภายนอก (เช่น `https://your-domain.com/line/callback`) จากนั้นกด **Verify** เพื่อทดสอบการเชื่อมต่อ

---

## 🛠️ คำสั่งสำหรับทดสอบและบำรุงรักษา (Maintenance Commands)

- **ทดสอบการโหลด Config และโมเดล**:
  ```bash
  ./venv/bin/python -c "import config; print('โมเดลปัจจุบัน:', config.GEMINI_MODEL)"
  ```
- **ทดสอบฟังก์ชันการแปลภาษา**:
  ```bash
  ./venv/bin/python -c "from translator import translate_message; print(translate_message('สวัสดีครับ ยินดีที่ได้รู้จัก'))"
  ```
