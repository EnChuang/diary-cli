# Score stepper（評分 ± 步進）

> **元件庫 ID**：`score-stepper`  
> **實作**：`ui/static/score-stepper.js` · `ui/static/style.css` · `generate.html`  

## Prompt

```text
.step-val {
  display: inline-block;
  min-width: 2ch; text-align: center;
  font-variant-numeric: tabular-nums;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.step-val.bump { transform: scale(1.3); }
.step-btn:active { transform: scale(0.9); }
```

點 ± 改 hidden input 分數，數字 `bump` scale 彈一下。
