# 🌐 LINE 简体中文 ⇄ 泰语 实时双向翻译机器人 (LINE Translate Bot)

[🇹🇭 ภาษาไทย (README_TH.md)](./README_TH.md) | [🇨🇳 简体中文 (README.md)](./README.md)

基于 **Flask** 与 **Google Gemini 3.8 Flash** 构建的 LINE 智能翻译机器人。专为 **LINE 群聊 (Group Chat)** 与私聊场景深度优化，实现简体中文与泰语之间的自动语系识别与流畅双向翻译。

---

## 📑 目录
- [系统架构与业务流程](#-系统架构与业务流程)
- [用户性别感知与精准敬语机制 (方案 1 + 方案 3)](#-用户性别感知与精准敬语机制-方案-1--方案-3)
- [项目目录结构](#-项目目录结构)
- [核心模块说明](#-核心模块说明)
- [环境变量配置 (.env)](#-环境变量配置-env)
  - [快速开始](#快速开始)
  - [变量说明](#变量说明)
  - [首次启动检查](#首次启动检查)
  - [换电脑时的设置](#换电脑时的设置)
  - [安全规则](#安全规则)
  - [如果密钥疑似泄露](#如果密钥疑似泄露)
  - [常见问题排查](#常见问题排查)
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
    D -- 是 --> F{是否为性别指令?\n'我是男生' / '我是女生'}

    F -- 是 (设置/查询指令) --> G[更新 SQLite 数据库 user_profiles.db]
    G --> H[回复确认消息并结束]

    F -- 否 (普通文本) --> I{是否需要翻译?\n含中文或泰文}
    I -- 否 (指令/纯英数/纯链接) --> J[静默忽略，不打扰群组]
    I -- 是 --> K[获取用户性别: 本地 SQLite 缓存 / Gemini 多模态初次推断]

    K --> L["调用 Google Gemini API (gemini-3.8-flash)"]
    L --> M["注入性别敬语 (男: ครับ/ผม, 女: ค่ะ/ดิฉัน, 中性: ทางเรา/ครับ)"]
    M --> N[获取高质量翻译结果]
    N --> O[添加国旗标识 🇹🇭 / 🇨🇳]
    O -->|LINE Messaging API 回复| B
    B -->|推送翻译消息至群组| A
```

---

## 🚻 用户性别感知与精准敬语机制 (方案 1 + 方案 3)

泰语非常注重讲话人的性别（敬语词如 `ครับ/ค่ะ`、人称代词如 `ผม/ฉัน/ดิฉัน`）。本项目融合 **用户主动指令（方案 1）** 与 **AI 多模态自动分析（方案 3）**，实现免配置与高精准度的平衡：

### 1. 用户交互指令（优先级最高）
群成员可在群聊或私聊中直接向机器人发送指令：

| 用户发送 | 机器人动作 | 机器人回复示例 |
| :--- | :--- | :--- |
| `我是男生` / `我是男` / `/male` / `ผมเป็นผู้ชาย` | 永久记住当前用户为 **男士** 👨 | `✅ 已记录您的性别为【男士】👨。后续翻译将适配男性专属敬语（ครับ / ผม）` |
| `我是女生` / `我是女` / `/female` / `ฉันเป็นผู้หญิง` | 永久记住当前用户为 **女士** 👩 | `✅ 已记录您的性别为【女士】👩。后续翻译将适配女性专属敬语（ค่ะ / ดิฉัน / ฉัน）` |
| `我的性别` / `/gender` / `เพศของฉัน` | 查询当前记录的性别与来源 | `ℹ️ 您当前登记的性别为：【男士】（来源：手动设置）` |
| `重置性别` / `/gender reset` / `รีเซ็ตเพศ` | 清除手动设定，恢复自动推断 | `🔄 已重置性别设置，后续将恢复通过昵称/头像自动识别` |

### 2. AI 多模态自动分析（零配置兜底）
当未设定过性别的用户首次在群聊发言时：
1. 自动通过 LINE Messaging API 获取用户资料（昵称与头像图片 URL）；
2. 调用 **Gemini 3.8 Flash** 多模态模型，结合名字文化背景与头像视觉进行性别推断（置信度要求 $\ge 75\%$）；若为风景/宠物/卡通/LOGO 或无法确定，则回退为通用中性；
3. 推断结果持久化写入本地 SQLite 数据库，**后续发言直接读取本地缓存（0.05ms），完全不影响翻译响应速度**。

### 3. 精准敬语对应规则
- **男士（`male`）**：使用男性礼貌结尾词 `ครับ`，第一人称代词使用 `ผม`；严禁女性语气词及斜杠双选。
- **女士（`female`）**：使用女性礼貌语气词 `ค่ะ`（陈述/回答）或 `คะ`（疑问），第一人称使用 `ดิฉัน` 或 `ฉัน`；严禁男性敬语及斜杠双选。
- **中性/未指定（`neutral`）**：使用通用商务敬语 `ครับ`，第一人称代词优先省略或使用 `ทาง我们`（`ทางเรา`），**严禁输出任何 `ครับ/ค่ะ`、`ผม/ฉัน` 等双拼选项**。

---

## 📂 项目目录结构

```text
translate_bot/
├── config.py           # ⚙️ 全局配置与环境变量加载（含启动自检）
├── main.py             # 🚀 Webhook 服务器入口（Flask + LINE SDK v3 + 异步防重）
├── translator.py       # 🧠 语言识别、多性别提示词注入与 Gemini 3.8 Flash 翻译引擎
├── user_manager.py     # 🚻 用户性别持久化存储（SQLite）与 Gemini 多模态推断
├── data/               # 💾 本地数据目录（user_profiles.db，已被 .gitignore 忽略）
├── tests/              # 🧪 自动化测试套件（test_gender_system.py）
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
| **`main.py`** | 1. 启动 Flask HTTP 服务，监听 `/line/callback`。<br>2. 验证 LINE 消息签名 (`X-Line-Signature`) 并以线程池异步处理，防 499 超时。<br>3. 拦截性别指令（`我是男生`、`我是女生` 等）直接中泰双语回复。<br>4. 普通消息调用 `user_manager` 提取或推断性别后传给翻译引擎。 |
| **`translator.py`** | 1. **语言判断**：通过正则表达式检测泰文字符 (`\u0e00-\u0e7f`) 与中文字符 (`\u4e00-\u9fa5`)。<br>2. **群聊降噪**：自动忽略以 `/`、`!`、`#` 开头的指令及网页链接，防止群聊刷屏。<br>3. **AI 翻译**：封装 `GeminiTranslator`，根据用户性别动态注入专用敬语规范，杜绝思考残留与斜杠双选。 |
| **`user_manager.py`** | 1. 本地 SQLite (`data/user_profiles.db`) 用户档案存储，支持手动设置与重置。<br>2. 首次发言基于昵称和头像图片调用 Gemini 3.8 Flash 多模态自动分析性别并入库。 |
| **`config.py`** | 1. 集中管理 LINE Token、Secret、Gemini API Key、模型名称及端口。<br>2. 提供 `validate_config()` 函数在启动时校验必要参数。 |

---

## 🔑 环境变量配置 (.env)

### 快速开始

第一次使用时，在项目目录执行：

```bash
cp .env.example .env
chmod 600 .env
```

用文本编辑器打开 `.env`，只在本机填写真实密钥。不要把真实密钥放入 README、Issue 或聊天记录。

### 变量说明

| 变量 | 必填 | 用途 | 从哪里取得/如何修改 |
| :--- | :--- | :--- | :--- |
| `LINE_CHANNEL_ACCESS_TOKEN` | 是 | LINE Messaging API 的访问令牌 | LINE Developers Console → Messaging API |
| `LINE_CHANNEL_SECRET` | 是 | 验证 LINE Webhook 签名 | LINE Developers Console → Basic settings |
| `GEMINI_API_KEY` | 是 | 调用 Google Gemini 翻译 | Google AI Studio |
| `GEMINI_MODEL` | 否 | 主要翻译模型；默认 `gemini-3.8-flash` | 修改 `.env` 中的模型名称 |
| `GEMINI_FALLBACK_MODEL` | 否 | 主模型失败时使用的备用模型；默认 `gemini-3.1-flash-lite` | 修改 `.env` 中的模型名称 |
| `SERVER_HOST` | 否 | 服务监听地址；默认 `0.0.0.0` | 通常保持默认值 |
| `SERVER_PORT` | 否 | 服务端口；默认 `8000` | 端口被占用时修改为其他数字 |

### 首次启动检查

先检查必要配置，再启动机器人：

```bash
./venv/bin/python -c "import config; config.validate_config()"
./venv/bin/python main.py
```

如果提示缺少变量，请回到 `.env` 补齐前三个必填值。检查时不要打印或复制密钥内容。

### 换电脑时的设置

在新电脑上克隆项目并创建本地配置：

```bash
git clone https://github.com/maccelectronic/macc-line-translate-bot.git
cd macc-line-translate-bot
cp .env.example .env
chmod 600 .env
```

然后从密码管理器或安全备份中恢复密钥到 `.env`。GitHub 仓库故意不包含 `.env`，所以不能从 GitHub 下载密钥。

### 安全规则

- 永远不要执行 `git add .env`；提交前用 `git status` 确认 `.env` 未被追踪。
- 可用以下命令检查 `.env` 是否被忽略，不会显示密钥值：
  ```bash
  git status --ignored --short .env
  ```
- 不要把密钥粘贴到 README、Issue、聊天或截图中。
- 如果权限不是仅所有者可读写，请执行 `chmod 600 .env`。

### 如果密钥疑似泄露

立即在 LINE Developers Console 和 Google AI Studio 撤销并重新生成对应密钥，更新本机 `.env` 后重启机器人。如果密钥曾经提交到 Git，不能只删除文件，必须先轮换密钥并清理 Git 历史。

### 常见问题排查

- `.env` 不存在：重新执行 `cp .env.example .env`。
- 必填值为空：填写 `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET` 和 `GEMINI_API_KEY`，然后重新运行配置检查。
- 权限过宽：执行 `chmod 600 .env`。
- 端口被占用：修改 `SERVER_PORT`，再重新启动。

下面是完整配置示例（仅使用占位符，不要直接填入真实密钥）：

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

- **运行全套自动化测试（数据库、性别推断、敬语输出）**：
  ```bash
  ./venv/bin/python tests/test_gender_system.py
  ```
- **测试环境变量与模型读取**：
  ```bash
  ./venv/bin/python -c "import config; print('当前模型:', config.GEMINI_MODEL)"
  ```
- **测试不同性别下的泰语敬语翻译**：
  ```bash
  ./venv/bin/python -c "
  import translator
  print('男士:', translator.translate_message('非常感谢，我现在通知工厂', gender='male'))
  print('女士:', translator.translate_message('非常感谢，我现在通知工厂', gender='female'))
  print('中性:', translator.translate_message('非常感谢，我现在通知工厂', gender='neutral'))
  "
  ```
- **Systemd 系统服务管理**：
  ```bash
  # 重启翻译服务
  sudo systemctl restart translate_bot.service

  # 查看服务实时运行状态
  sudo systemctl status translate_bot.service

  # 实时查看系统运行日志
  sudo journalctl -u translate_bot.service -f
  ```
