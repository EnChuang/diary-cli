# 待做（Yes Log / diary-cli）

> 更新：2026-08-01（檔案整理後）  
> **可還原**：[`MILESTONES.md`](./MILESTONES.md) → `v0.2.1`／`v0.2.0`  
> **核心地圖（本機）**：`design/product/CORE-FILES.md`  
> **進度細節（本機）**：`dev-local/SESSION.md`

---

## 已完成（近期）

| 項 | 狀態 |
|----|------|
| Web 主路徑（新增／cast／追問／生成／落盤／後續／刪除／wipe） | ✅ |
| BYOK：`.env` 本機／`.env.example`+SETUP 上 GitHub | ✅ |
| 評分 skill C1 校準＋金標 v1＋對拍 | ✅ |
| §2 同情節不同心情 → 入 skill | ✅ |
| 里程碑 v0.2.0／v0.2.1 | ✅ |
| 檔案整理（刪退役 score 頁、舊 scratch） | ✅ |

---

## 進行中／待完成（建議順序）

### A. 評分核心（慢而細）— **主軸**

| 優先 | 項 | 說明 | 狀態 |
|------|----|------|------|
| 1 | **深度校準 §1～§12** | [`design/scoring/05-deep-calibration.md`](design/scoring/05-deep-calibration.md) | 🔄 §1§2 完成；**§3 起待續** |
| 2 | 每段共識 → 寫入 skill | 未點頭不改 | 🔄 |
| 3 | 金標擴充 | 新條款加 fixture；`run_gold_v1.py` | ⬜ |
| 4 | C2 完整篇 | [`c2-full-scenarios.md`](design/scoring/c2-full-scenarios.md) 可選 | ⬜ |
| 5 | 長版 skill few-shot | 可選再加厚 | ⬜ |

### B. 產品體驗（次要）

| 項 | 說明 | 狀態 |
|----|------|------|
| UI 視覺精修 | 新增／閱讀對 design | ⬜ |
| ui-discuss 與實作同步 | 文件過時處 | ⬜ |
| 只重跑 AI 評分 | 不重生成稿 | ⬜ |
| 單元測試／匯出 | Phase J | ⬜ |

### C. 商業化整理（有對外需求時）

| 項 | 說明 | 狀態 |
|----|------|------|
| 一頁紙 pitch | 見 `design/product/COMMERCIALIZATION.md` | ⬜ |
| 對外評分哲學摘要 | 從 scoring 蒸餾 1～2 頁 | ⬜ |

---

## 下次開聊可直接說

1. 「繼續深度校準 §3」  
2. 「把 §x 收進 skill」  
3. 「調某某頁 UI」  
4. 「寫一頁紙商業說明」  

---

## 勿做

- 勿 commit `.env`、jsonl 全文、`dev-local/`、`CORE-FILES.md`  
- 勿回顯 API Key  
- 勿任意搬移 `ui/` / `storage/` / `skill/`  
