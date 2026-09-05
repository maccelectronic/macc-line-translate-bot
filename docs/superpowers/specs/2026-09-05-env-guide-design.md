# .env 使用指南設計

## 目標

在中文與泰文 README 中提供一致、可在新電腦重現的 `.env` 設定說明，讓使用者知道如何建立本機設定、驗證必要變數，以及避免把秘密提交到 GitHub。

## 文件範圍

- 修改 `README.md`：新增簡體中文 `.env` 使用指南。
- 修改 `README_TH.md`：新增對應泰文 `.env` 使用指南。
- 不修改 Python 程式、`.env`、`.env.example` 或 GitHub 倉庫設定。

## 內容設計

兩份指南使用相同順序與命令：

1. 從 `.env.example` 建立 `.env`：`cp .env.example .env`。
2. 說明三組必要秘密：LINE channel access token、LINE channel secret、Gemini API key。
3. 說明非秘密設定：主要/備用模型、伺服器 Host 與 Port。
4. 啟動前以 `grep` 或現有設定檢查命令確認必要值已填寫，不在輸出中列印秘密。
5. 強調 `.env` 已被 `.gitignore` 忽略，禁止 `git add .env`、禁止貼到 README、聊天或公開 issue。
6. 說明新電腦只會取得 `.env.example`，秘密必須從密碼管理器或安全備份還原。
7. 說明若懷疑外洩，立即在 LINE Developers 與 Google AI Studio 撤銷並重新產生金鑰。
8. 提供常見錯誤：檔名錯誤、未填值、權限過寬、端口衝突，以及相應處理方式。

所有範例只使用 `your_..._here` 佔位符；不得把本機 `.env` 或真實金鑰複製到任何 README。

## 驗證

- 兩份 README 都包含完整指南，且步驟順序與命令一致。
- Markdown 代碼區塊成對閉合，連結與目錄錨點不破壞。
- `git diff --check` 通過。
- Git 追蹤檔案與歷史中沒有 `.env`、金鑰值、`venv/` 或 `.pyc`。
- README 修改提交後推送到現有私人倉庫，並確認遠端 `main` 與本機 commit 一致。
