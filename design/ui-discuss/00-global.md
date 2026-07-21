# 00 · 全站殼與設計總則

## 現況（程式）

- 路由：全站  
- 模板：`ui/templates/base.html`（固定半透明頂欄 · **淺色**）  
- 樣式：`ui/static/style.css`（**使用者色票已套**）  

## 規格鎖定

- 介面語言：繁體中文  
- 本機單人  
- 參考：`design/styles/apple-design`（克制、層級、按壓 scale、系統字、reduced-motion）  
- 產品語意優先於炫技  

## 已決（2026-07-20 · 色票改版）

| 項目 | 決議 |
|------|------|
| 模式 | **淺色**（bg-100 底 + 白卡片） |
| 來源色票 | 見下表（鎖定） |
| 主色／CTA | primary-100 `#c21d03`；hover primary-200 |
| 軟強調 | primary-300（問句框、排名銅） |
| 中性 | accent-100 字重／圖示；accent-200 邊框輔助 |
| 文字 | text-100 主、text-200 次 |
| 背景 | bg-100 頁、bg-200 升高、bg-300 邊線 |
| 成功分 | 獨立綠（榜＋分；色票無綠故保留語意色） |
| 危險 | 同 primary-100 |
| 字體 | 系統堆疊不變 |
| 頂欄 | 淺霜 + blur |
| 內容寬 | max-width ~42rem |

### 來源色票

```css
--primary-100: #c21d03;
--primary-200: #fd5732;
--primary-300: #ffb787;
--accent-100:  #393939;
--accent-200:  #bebebe;
--text-100:    #232121;
--text-200:    #4b4848;
--bg-100:      #fbfbfb;
--bg-200:      #f1f1f1;
--bg-300:      #c8c8c8;
```

## 討論中

- 是否再加深色模式切換？  
- 成功綠是否要改成偏灰的 accent 系？  

## 待做

- [x] 全站 token 與殼（淺色色票）  
- [x] 01-home 對齊新色  
- [ ] 分畫面 refining：下一步 **02-new-event**（或回饋微調）  

## 如何預覽

```powershell
uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765
```

開 http://127.0.0.1:8765  
