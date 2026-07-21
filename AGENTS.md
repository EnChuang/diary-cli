# diary-cli — Agent 交接與工作說明

**庫根**：`C:\DATA\A_Developement\Project\diary-cli`  
人類測試說明：**[USAGE.md](./USAGE.md)**（勿與本檔混淆）。

---

## 一句話

**八卦編年史 CLI**：多輪補全 → 成稿 → 非本人主觀評分 → 歷史榜。  
本機 BYOK（ModelArk）+ Skill + 確認落盤；**無日記路徑**（已退役）。

哲學：AI 草稿／建議分；**確認後才落盤**。  
角色：只辨識「有人出現」；同一性靠 **merge**（D18）。  
UI：D19–D24。草稿**僅 1 份**；詢問框**只在新增／後續**（冷啟動不彈）。後續規格：`ui-discuss/08-sequel.md`（未實作）。  
文字：一律**繁體**（`text_zh`）。

本機文件（**不進 Git**）：`dev-local/SESSION.md` · `PRODUCT_PLAN.md` · `DATA_CONTRACT.md`

---

## 目錄

```text
diary-cli/
├── USAGE.md · README.md · AGENTS.md
├── design/               ← 素材 + **ui-discuss/ 分階段討論**
├── ui/                   ← 本機 Web 殼
├── gossip.py · story_*.py · board.py
├── llm_client.py · text_zh.py
├── skill/ · storage/ · data/ · dev-local/
```

---

## 執行

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
.\.venv\Scripts\activate
python gossip.py
python board.py rank
uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765
# 設計：design/README.md；UI 討論：design/ui-discuss/（分階段）
```

`ARK_API_KEY` 必填。禁止回顯 Key、禁止 commit `.env`／jsonl 全文／`dev-local/`。

改文筆 → **`skill/story_*.md`**。改儲存／評分公式 → `storage/` + DATA_CONTRACT。

---

## 已完成 / 下一步

- ✅ Phase A～H（CLI 主路徑）；繁體；日記退役；USAGE  
- ✅ N1 D22 標題 CLI（`--title`／`--title-ai`／互動）  
- ➡️ **下一步見 SESSION**（預設 N2／N3 UI 殼、D21 閱讀）  
- 可選 Phase J：單元測試、匯出  

未指定時讀 SESSION，小步改，勿整包重寫。對話用**繁體中文**。

### 冷啟動

```text
讀 dev-local/SESSION.md（收工狀態）→ USAGE → AGENTS。
設計：design/README.md；apple-design 在 design/styles/apple-design/。
CLI：gossip.py · UI：uvicorn ui.app:app --port 8765
A～H + N1 + ui 殼起步已完成。下一刀預設：依 design 調 ui 視覺。
無日記路徑。勿整包重寫。
```
