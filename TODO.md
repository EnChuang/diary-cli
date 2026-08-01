# 待做（Yes Log / diary-cli）

> 根目錄提醒用。完成一項可勾選或移到「已完成」。  
> 更新：2026-08-01  
> 詳細狀態：`dev-local/SESSION.md`（不進 Git）  
> **可還原**：[`MILESTONES.md`](./MILESTONES.md) → tag **`v0.2.0`**（`2c4b699`）

---

## 高優先 · 評分核心（產品心）

詳細計畫：

**→ [`design/scoring/00-score-core-plan.md`](design/scoring/00-score-core-plan.md)**

| 項 | 說明 | 狀態 |
|----|------|------|
| P0 計畫定案 | 哲學、陷阱、校準流程 | ✅ 文件已有 |
| P1 人類短題校準 | AI 出 10 情境，主人答分帶＋理由 | ⬜ **下次優先** |
| P2 陷阱目錄 + 金標 v1 | T01–T18、固定測資 | ⬜ |
| P3 長版 `skill/story_score.md` | 不限篇幅、可換環境重現 | ⬜（現為防誤判短／中版） |
| P4 評分回歸腳本 | 改 skill／換模型必跑 | ⬜（煙測在 `dev-local/scratch/`） |
| P5 換模型壓力測 | 可選 | ⬜ |
| P6 只重跑評分按鈕等 | 可選產品項 | ⬜ |

執行中規則：[`skill/story_score.md`](skill/story_score.md)

---

## 產品／工程

| 項 | 說明 | 狀態 |
|----|------|------|
| 事件刪除 | 詳情頁才有；子不刪父；父連子孫；ledger 重算；回首頁 | ✅ |
| 評語可編 | 落盤前可改 AI 評語 | ✅ |
| 跳過 UX | loading；無下一問→補充確認提示 | ✅ |
| 生成頁不狂刷 | 評分中不因 has_story 整頁重載 | ✅ |
| 一鍵銷毀 | 頁腳 + 確認 | ✅ |
| D21 閱讀體驗精修 | 依 design 再調 | ⬜ |
| UI 視覺對 design | 新增／閱讀等 | ⬜ |
| ui-discuss 文件同步 | 與實作對齊 | ⬜ |
| 單元測試／匯出 | Phase J 可選 | ⬜ |

---

## 下次開聊可直接說

1. 「開始評分校準 C1」→ 依計畫出 10 題短情境  
2. 「蒸餾長版 story_score」→ 在校準後升級 skill  
3. 「調某某頁 UI」→ 對 design/ui-discuss  

---

## 勿做

- 勿 commit `.env`、jsonl 全文、`dev-local/`  
- 勿回顯 API Key  
- 勿任意搬移 `ui/` / `storage/` / `skill/` 破壞路徑  
