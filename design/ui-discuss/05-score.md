# 05 · 評分建議與落盤

## 現況（程式）2026-08-01

- 評分已併入 **`/events/{id}/generate`**（成稿後同頁調分）  
- 舊 `/score` 導向 generate  
- 操作：AI 建議分 → **± 調分** → **評語可編** → 確認落盤  
- 規則：本場平均 ±10、不評「我」、confirm → ledger；觀感分見 skill  

## 規格鎖定

- 分數語意＝**使用者主觀觀感**（非道德／可怜）  
- 確認才寫歷史榜；材料含主文／問答／成稿  

## 已決

| 日期 | 決議 | 備註 |
|------|------|------|
| 2026-08-01 | Web 調分＋評語可編 | generate 頁 |
| 2026-08-01 | 評分核心長線計畫 | `design/scoring/` |

## 待做

- [ ] 人類校準 C1 → 長版 skill／金標（見 scoring plan）  
- [ ] （可選）只重跑 AI 評分、不重生成稿  

## 參考

- **評分核心計畫**：[`design/scoring/00-score-core-plan.md`](../scoring/00-score-core-plan.md)  
- 執行 skill：[`skill/story_score.md`](../../skill/story_score.md)  
