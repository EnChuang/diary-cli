# AI button spinner

> **元件庫 ID**：`ai-button-spinner`  
> **實作**：`ui/static/ai-loading.js` · `.btn-ai` / `.spinner` in style.css  

## Prompt

```css
.spinner {
  width: 44px; height: 44px;
  border-radius: 50%;
  border: 4px solid #232326;
  border-top-color: #FF8A00;
  border-right-color: #FF8A00;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(1turn); } }
```

表單 `data-ai-form` 送出時，`data-ai-submit` 按鈕加 `is-loading`，標籤隱藏、顯示 spinner。  
按鈕內 spinner 縮為 ~1.15rem 以配合主按鈕高度；色調沿用 #FF8A00。
