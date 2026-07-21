# 野史錄 · Yes Log（diary-cli）

本機單人**野史錄**（English: **Yes Log**）：Skill + [ModelArk](https://www.byteplus.com/en/product/ModelArk) BYOK + **確認後才落盤**。

```text
主文 → 初稿 → 追問 → 成稿 → 評分確認 → 歷史榜
```

**測試用法與完整規則 → [USAGE.md](./USAGE.md)**  
**AI Agent 交接 → [AGENTS.md](./AGENTS.md)**

---

## 目錄一覽

| 路徑 | 用途 |
|------|------|
| `gossip.py` | **CLI 主入口**（完整流程） |
| `story_*.py` | 初稿／追問／成稿／評分（可分步） |
| `board.py` | 榜單與閱讀 |
| `ui/` | **本機 Web UI**（FastAPI + 模板） |
| `design/brand/` | 品牌 Logo 素材（暫不嵌 UI） |
| `run_ui.ps1` | UI 啟動腳本（建議 `-NoReload` 測 AI） |
| `skill/` | AI 提示詞（改行為優先改這裡） |
| `storage/` | 本地 jsonl 讀寫、評分約束、merge |
| `data/` | 你的資料（不進 Git） |
| `dev-local/` | 構想／契約（不進 Git） |
| `llm_client.py` · `text_zh.py` | API 與繁體 |

---

## 安裝

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 編輯 .env，填入 ARK_API_KEY
```

## 快速開始

### 本機網頁 UI

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
# 建議（測 AI 較穩）：
.\run_ui.ps1 -NoReload
# 或熱重載開發：
.\run_ui.ps1
```

瀏覽器開：<http://127.0.0.1:8765>  
功能：歷史榜（眼睛顯示全名）、防窺滑動解鎖、新增／後續、追問、AI 生成＋調分落盤。  
**風格素材 → [`design/`](design/)** · **分階段 UI 討論 → [`design/ui-discuss/`](design/ui-discuss/)**

### CLI

```powershell
python gossip.py
python board.py rank
```

更多 → **[USAGE.md](./USAGE.md)**。

---

## 環境變數

| 變數 | 說明 |
|------|------|
| `ARK_API_KEY` | 必填 |
| `ARK_BASE_URL` | 可選 |
| `ARK_MODEL` | 可選，須已開通 |

## 安全

- 事件內容會送至 ModelArk  
- 勿提交 `.env`、`data/*.jsonl`、`dev-local/`  
