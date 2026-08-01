# diary-cli — Agent 交接與工作說明

**庫根**：`C:\DATA\A_Developement\Project\diary-cli`  
人類測試說明：**[USAGE.md](./USAGE.md)**（勿與本檔混淆）。  
待辦勾選：**[TODO.md](./TODO.md)**。

---

## 一句話

**野史錄（Yes Log）**：多輪補全 → 成稿 → **非本人主觀觀感分** → 歷史榜。  
本機 BYOK（ModelArk）+ Skill + **確認後才落盤**；**無日記路徑**（已退役）。

哲學：AI 草稿／建議分／建議評語；**確認後才落盤**（分數與評語皆可改）。  
評分：評「使用者對此人的觀感」，**不是**道德分／可怜分；計畫見 `design/scoring/`。  
角色：只辨識「有人出現」；同一性靠 **merge**（D18）。  
UI：草稿**僅 1 份**；詢問框只在新增／後續（冷啟動不彈）。後續、出場確認、刪除、wipe **已接 Web**。  
文字：一律**繁體**（`text_zh`）。

本機文件（**不進 Git**）：`dev-local/SESSION.md` · `PRODUCT_PLAN.md` · `DATA_CONTRACT.md`

---

## 目錄

```text
diary-cli/
├── README.md · USAGE.md · AGENTS.md · TODO.md
├── design/               ← 素材 + ui-discuss/ + scoring/
├── ui/                   ← 本機 Web（app.py · templates · static）
├── gossip.py · story_*.py · board.py
├── llm_client.py · text_zh.py
├── skill/ · storage/ · data/ · dev-local/
└── run_ui.ps1
```

**勿任意搬移**會被 import 或模板引用的路徑（尤其 `ui/`、`storage/`、`skill/`）。

---

## 執行

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
.\.venv\Scripts\activate
python gossip.py
python board.py rank
.\run_ui.ps1 -NoReload
# 或：uvicorn ui.app:app --host 127.0.0.1 --port 8765
# 熱重載：.\run_ui.ps1  （reload-dir：ui、storage、skill）
```

`ARK_API_KEY` 必填。禁止回顯 Key、禁止 commit `.env`／jsonl 全文／`dev-local/`。

| 改什麼 | 改哪 |
|--------|------|
| 文筆／追問／成稿／**評分標準** | `skill/story_*.md` |
| 儲存、刪除、±10、落盤 | `storage/` + DATA_CONTRACT |
| Web 流程／畫面 | `ui/` + `design/ui-discuss/` |
| 評分長線（校準、金標） | `design/scoring/` |

---

## 已完成 / 下一步（2026-08-01）

- ✅ Phase A～H（CLI）；繁體；日記退役；USAGE  
- ✅ N1 標題；Web 主路徑：新增／cast／追問／生成 job／調分落盤／後續／草稿 dialog  
- ✅ 評分 skill 防誤判；評語可編；事件刪除（詳情進；父連子孫；重算榜）；跳過 UX  
- ✅ `design/scoring/00-score-core-plan.md`、根目錄 `TODO.md`  
- ➡️ **下一步**：評分校準 C1，或 UI 視覺（見 SESSION）  
- 可選：單元測試、匯出、只重跑評分  

未指定時讀 **`dev-local/SESSION.md`** + **`TODO.md`**，小步改，勿整包重寫。對話用**繁體中文**。

### 冷啟動

```text
讀 dev-local/SESSION.md → TODO.md → USAGE → AGENTS。
設計：design/README.md；評分計畫：design/scoring/。
CLI：gossip.py · UI：.\run_ui.ps1 -NoReload → :8765
A～H + Web 主路徑已完成。下一刀預設：評分校準 C1 或依使用者。
無日記路徑。勿整包重寫。勿搬移破壞 import 的目錄。
```
