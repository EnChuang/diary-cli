# 野史錄 · Yes Log（diary-cli）

本機單人**野史錄**（English: **Yes Log**）：把職場／生活八卦寫成可讀短篇，並對**出場他人**打上你的主觀分數，累積歷史榜。

```text
主文 → 初稿 → 確認出場 → 多輪追問 → 成稿 → 建議分（可改分數／評語）→ 確認落盤 → 歷史榜
```

- **AI**：本機 [ModelArk](https://www.byteplus.com/en/product/ModelArk) **BYOK**（你自己的 Key）  
- **落盤哲學**：AI 只出草稿／建議分；**你確認後**才寫入本機 jsonl  
- **評分語意**：**你對此人的觀感**（非道德判決、非「誰可憐誰高分」）  
- **無日記路徑**（已退役）

| 文件 | 給誰 |
|------|------|
| **[USAGE.md](./USAGE.md)** | 你：怎麼測、完整規則 |
| **[AGENTS.md](./AGENTS.md)** | AI Agent 交接 |
| **[TODO.md](./TODO.md)** | 待辦勾選（含評分核心） |
| **[MILESTONES.md](./MILESTONES.md)** | **Git 可還原節點**（如 `v0.2.0`） |
| **`dev-local/SESSION.md`** | 本機進度（不進 Git） |

---

## 目錄一覽

| 路徑 | 用途 |
|------|------|
| `gossip.py` | CLI 主入口（完整流程） |
| `story_*.py` | 初稿／追問／成稿／評分（可分步） |
| `board.py` | 榜單與閱讀（CLI） |
| `ui/` | **本機 Web UI**（FastAPI + Jinja + static） |
| `run_ui.ps1` | UI 啟動（建議 `-NoReload` 測 AI） |
| `skill/` | AI 提示詞（改文筆／評分標準優先改這裡） |
| `storage/` | 本地 jsonl、±10 約束、落盤、刪除、merge |
| `data/` | 你的資料（**不進 Git**） |
| `design/` | 設計素材、`ui-discuss/`、**`scoring/` 評分計畫** |
| `dev-local/` | 構想／契約／SESSION（**不進 Git**） |
| `llm_client.py` · `text_zh.py` | API 與繁體 |
| `TODO.md` | 根目錄待辦提醒 |

路徑請勿任意搬移：`ui`↔`storage`↔`skill` 互相 import／讀檔，**相對位置固定**。

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

---

## 快速開始

### 本機網頁 UI（主要使用）

```powershell
.\.venv\Scripts\activate
# 測 AI 建議（避免 reload 掐斷長請求）：
.\run_ui.ps1 -NoReload
# 改 UI 熱重載：
.\run_ui.ps1
```

瀏覽器：<http://127.0.0.1:8765>

| 能力 | 說明 |
|------|------|
| 首頁 | 歷史榜（眼睛顯全名）+ 事件列表；防窺滑動解鎖 |
| 新增／後續 | 標題手填或交給 AI；全庫僅 1 份草稿 |
| 確認出場 | 人名／刪職稱誤認 |
| 追問 | 回答、**跳過**（有 loading）、到此為止 |
| 成稿／評分 | 背景生成；可調分、**可改評語**後落盤 |
| 事件詳情 | 閱讀；工具列**刪除**（父連刪子孫、重算榜） |
| 頁腳 | 一鍵銷毀本機資料（不刪 .env） |

**設計** → [`design/`](design/) · **UI 分階段** → [`design/ui-discuss/`](design/ui-discuss/) · **評分長線** → [`design/scoring/`](design/scoring/)

### CLI

```powershell
python gossip.py
python board.py rank
```

細節 → **[USAGE.md](./USAGE.md)**。

---

## 環境變數

| 變數 | 說明 |
|------|------|
| `ARK_API_KEY` | 必填 |
| `ARK_BASE_URL` | 可選 |
| `ARK_MODEL` | 可選，須已開通 |

---

## 安全

- 事件內容會送至 ModelArk  
- **勿提交** `.env`、`data/*.jsonl`、`dev-local/`  
- 勿在對話或 commit 中回顯 API Key  

---

## 進度摘要（2026-08-01）

- ✅ CLI 主路徑 A～H；Web 主流程（含後續、出場、生成、落盤）  
- ✅ 觀感分 skill 初版防誤判；評語可編；事件刪除與榜重算  
- ➡️ **下一步**：評分校準 C1（見 `TODO.md` / `design/scoring/00-score-core-plan.md`）  
- 可選：UI 視覺精修、單元測試、匯出  

本機最新收工狀態：**`dev-local/SESSION.md`**。
