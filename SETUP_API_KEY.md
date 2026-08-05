# 設定 API Key（BYOK）

本專案**不會**、也**不應**把任何人的 API Key 放上 GitHub。

## 兩個檔案，各司其職

| 檔案 | 在 GitHub？ | 誰用 | 內容 |
|------|-------------|------|------|
| **`.env.example`** | ✅ 會上傳 | 所有 clone 的人 | **無真 Key**，只有欄位說明與占位 |
| **`.env`** | ❌ 永不上傳 | 你自己／每位使用者本機 | **自己的** `ARK_API_KEY` |

```text
GitHub 倉庫                    你的電腦（開發）
─────────────────              ─────────────────
.env.example  ──copy──►  .env  （填入你的 Key）
（無真 Key）                   ↑
                               git 不同步此檔（.gitignore）
```

- **你開發**：日常改 code、`git push` 即可；**不要** `git add .env`。  
- **別人重現**：clone → 複製範本 → 填**他自己的** Key → 啟動。

---

## 從 GitHub 重現操作（給 clone 的人）

```powershell
git clone https://github.com/EnChuang/diary-cli.git
cd diary-cli

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 建立本機 .env（從範本；不會產生真 Key）
.\setup_env.ps1

# 編輯 .env，將 ARK_API_KEY=ark-你的金鑰 改成控制台的真 Key
notepad .env

# 啟動
.\run_ui.ps1 -NoReload
```

瀏覽器打開：http://127.0.0.1:8765

### 金鑰哪裡申請？

- BytePlus ModelArk 或 火山引擎方舟控制台 → API Key（通常為 `ark-...`）  
- 並確認 `ARK_MODEL`／`ARK_BASE_URL` 與你帳號已開通的模型一致（見 `.env.example` 註解）

---

## 你自己開發時

1. 本機已有 `.env` 且含你的 Key → **保持即可**，平常 push 不會帶上它。  
2. 若誤刪 `.env`：再跑 `.\setup_env.ps1`，再填一次 Key。  
3. 檢查是否被追蹤：`git status` 不應出現 `.env`；`git check-ignore -v .env` 應顯示被忽略。

---

## 安全

- 勿把 `.env` 內容貼到 Issue、PR、聊天、截圖  
- 若 Key 曾外洩：到控制台作廢並換新  
- 倉庫內只有 [`.env.example`](./.env.example)，**沒有**作者可用的真金鑰  
