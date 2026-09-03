# 🌐 LINE 简体中文 ⇄ 泰语 实时双向翻译机器人 (LINE Translate Bot)

[🇹🇭 ภาษาไทย (README_TH.md)](./README_TH.md) | [🇨🇳 简体中文 (README.md)](./README.md)

基于 **Flask** 与 **Google Gemini 3.7 Flash** 构建的 LINE 智能翻译机器人。专为 **LINE 群聊 (Group Chat)** 与私聊场景深度优化，实现简体中文与泰语之间的自动语系识别与流畅双向翻译。

---

## 📑 目录
- [系统架构与业务流程](#-系统架构与业务流程)
- [项目目录结构](#-项目目录结构)
- [核心模块说明](#-核心模块说明)
- [环境变量配置 (.env)](#-环境变量配置-env)
- [安装与启动指南](#-安装与启动指南)
- [LINE 群聊部署关键设置](#-line-群聊部署关键设置)
- [日常维护与测试命令](#-日常维护与测试命令)

---

## 🏗️ 系统架构与业务流程

```mermaid
flowchart TD
    A[👤 LINE 群聊 / 私聊用户] -->|发送文字消息| B[LINE 官方服务器]
    B -->|Webhook POST /line/callback| C["Flask 应用服务器 (main.py)"]
    C -->|验证 X-Line-Signature 签名| D{签名是否合法?}
    D -- 否 --> E[返回 400 Bad Request]
    D -- 是 --> F["翻译处理核心 (translator.py)"]
    
    F -->|过滤指令与链接 / ! # http| G{是否需要翻译?}
    G -- 否 (指令/纯英数/纯链接) --> H[静默忽略，不打扰群组]
    G -- 是 (含中文或泰文) --> I["调用 Google Gemini API"]
    
    I -->|主模型: gemini-3.7-flash| J{API 请求状态}
    J -- 成功 --> K[获取翻译结果]
    J -- 异常/额度耗尽 --> L["自动降级备用模型 (gemini-3.1-flash-lite)"] --> K
    
    K --> M[添加国旗标识 🇹🇭 / 🇨🇳]
    M -->|LINE Messaging API 回复| B
    B -->|推送翻译消息至群组| A
```

---

## 📂 项目目录结构

```text
translate_bot/
├── config.py           # ⚙️ 全局配置与环境变量加载（含启动自检）
├── main.py             # 🚀 Webhook 服务器入口（Flask + LINE SDK v3）
├── translator.py       # 🧠 语言识别、群聊噪声过滤与 Gemini 3.7 Flash 翻译引擎
├── .env                # 🔑 本地敏感密钥配置（禁止提交至 Git）
├── .env.example        # 📝 环境变量配置模板
├── requirements.txt    # 📦 Python 依赖包清单
├── .gitignore          # 🚫 Git 忽略规则
├── README.md           # 📖 中文项目说明手册
└── README_TH.md        # 📖 คู่มือการใช้งานและโครงสร้างระบบภาษาไทย
```

---

## 🧩 核心模块说明

| 文件名 | 职责说明 |
| :--- | :--- |
| **`main.py`** | 1. 启动 Flask HTTP 服务，监听 `/line/callback`。<br>2. 验证 LINE 消息签名 (`X-Line-Signature`)。<br>3. 接收并解析 `MessageEvent`，调用翻译模块后通过 `reply_message` 自动回复。 |
| **`translator.py`** | 1. **语言判断**：通过正则表达式检测泰文字符 (`\u0e00-\u0e7f`) 与中文字符 (`\u4e00-\u9fa5`)。<br>2. **群聊降噪**：自动忽略以 `/`、`!`、`#` 开头的指令及网页链接，防止群聊刷屏。<br>3. **AI 翻译**：封装 `GeminiTranslator`，使用 `gemini-3.7-flash` 模型进行高质量中泰双向互译，内置备用模型故障自动转移。 |
| **`config.py`** | 1. 集中管理 LINE Token、Secret、Gemini API Key、模型名称及端口。<br>2. 提供 `validate_config()` 函数在启动时校验必要参数。 |

---

## 🔑 环境变量配置 (.env)

复制 `.env.example` 为 `.env` 并填写对应密钥：

```ini
# ==========================================
# LINE Bot 配置 / การตั้งค่า LINE Bot
# ==========================================
# LINE Developers Console -> Messaging API -> Channel access token (long-lived)
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here

# LINE Developers Console -> Basic settings -> Channel secret
LINE_CHANNEL_SECRET=your_line_channel_secret_here

# ==========================================
# Gemini AI 配置 / การตั้งค่า Gemini AI
# ==========================================
# Google AI Studio 获取 API Key (https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# 主要翻译模型（当前推荐 gemini-3.7-flash）
GEMINI_MODEL=gemini-3.7-flash

# 备用容错模型（当主模型遇到 404 或限额时自动启用）
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite

# ==========================================
# 服务器配置 / การตั้งค่าเซิร์ฟเวอร์
# ==========================================
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

---

## 🚀 安装与启动指南

### 1. 创建虚拟环境并安装依赖
```bash
cd /home/ubuntu/Desktop/translate_bot

# 创建 Python 虚拟环境 (如未创建)
python3 -m venv venv

# 安装依赖
./venv/bin/pip install -r requirements.txt
```

### 2. 前台启动测试
```bash
./venv/bin/python main.py
```

### 3. 后台守护运行 (nohup 方式)
```bash
# 后台启动并将日志写入 bot.log
nohup ./venv/bin/python main.py > bot.log 2>&1 &

# 查看实时运行日志
tail -f bot.log

# 检查运行进程
ps aux | grep main.py
```

---

## 📌 LINE 群聊部署关键设置

在 [LINE Official Account Manager](https://manager.line.biz/) 后台务必确认以下 3 项设置：

1. **允许加入群组**：
   - 路径：**设置 (Settings)** -> **账号设置 (Account settings)** -> 开启 **「允许加入群组或多人聊天室 (Allow bot to join group chats)」**。
2. **关闭官方自动回复**：
   - 路径：**回应设置 (Response settings)** -> 响应模式选择 **「聊天机器人 (Bot)」** -> 将 **「自动回应消息 (Auto-reply messages)」关闭 (OFF)**（避免用户在群里发言时触发 LINE 默认罐头回复）。
3. **启用 Webhook**：
   - 路径：在 LINE Developers Console -> Messaging API 页面，开启 **「Use webhook」**，填入公网地址（如 `https://your-domain.com/line/callback`），点击 **Verify** 确认联通。

---

## 🛠️ 日常维护与测试命令

- **测试环境变量与模型读取**：
  ```bash
  ./venv/bin/python -c "import config; print('当前模型:', config.GEMINI_MODEL)"
  ```
- **测试翻译函数**：
  ```bash
  ./venv/bin/python -c "from translator import translate_message; print(translate_message('สวัสดีครับ ยินดีที่ได้รู้จัก'))"
  ```
