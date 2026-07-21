# 05 · 評分建議與落盤

## 現況（程式）

- 路由：`GET/POST /events/{id}/score`  
- 模板：`ui/templates/score.html`  
- 操作：**取得 AI 建議分**、**確認落盤**  
- 規則：本場平均 ±10、不評「我」、confirm → ledger  

## 規格鎖定

- 分數語意＝使用者主觀；可改分後再落盤（CLI 有調分；**Web 調分 UI 尚未做**）  
- 確認才寫歷史榜  
- 材料含問答（使用者補充會影響建議分）  

## 討論中

- （Web 是否要做每人分數輸入框／滑桿）

## 已決

| 日期 | 決議 | 備註 |
|------|------|------|
| | | |

## 待做（實作）

- [ ] UI 調分（對齊 CLI interactive_adjust）  
- [ ] 落盤成功回饋後導向 D21 閱讀頁  

## 參考素材

- styles：  
- motion：  
- references：`05-score-*.png`  
