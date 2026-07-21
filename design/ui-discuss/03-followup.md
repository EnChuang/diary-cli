# 03 · 追問迴圈

## 現況（程式）

- 路由：`GET/POST /events/{id}/followup`  
- 模板：`ui/templates/followup.html`  
- 操作：**送出回答**、**跳過**、**到此為止**  

## 規格鎖定（D20）

- **必須有「跳過」按鈕**（對應 CLI `跳過` → 存「（跳過）」）  
- 跳過 ≠ 結束整場；結束用「到此為止」→ `awaiting_generate`  
- 跳過鈕應與送出同級可見，勿藏很深  
- CLI 僅精確詞「跳過」；UI 靠按鈕，不要求記指令  

## 討論中

- 

## 已決

| 日期 | 決議 | 備註 |
|------|------|------|
| 2026-07-19 | D20；Web 已有三鈕 | 樣式待 design |

## 待做（實作）

- [ ] 跳過／到此為止視覺層級（主／次／危險）  
- [ ] 問答時間軸可讀性  

## 參考素材

- styles：apple-design（回饋 on press）  
- motion：  
- references：`03-followup-*.png`  
