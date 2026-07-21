# 動效／CSS 動畫參考

> 總規範與素材清冊：上一層 [`../README.md`](../README.md)

**可以給 CSS 動畫。** 推薦放法：

## 怎麼丟

| 方式 | 做法 |
|------|------|
| **檔案** | 每個片段一個檔：`snippets/01-fade-up.css` 或 `.md`（內含 code fence） |
| **連結** | 寫在 `links.md`（CodePen、文章、GitHub） |
| **截圖／錄影** | 可放 `design/references/`，並在 `links.md` 註「對應哪個動畫」 |

## 建議檔名

```text
design/motion/snippets/
  01-button-press.css
  02-card-enter.css
  03-sheet-spring.md
design/motion/links.md
```

## 給 AI 時怎麼說

- 「套用 `design/motion/snippets/02-card-enter.css` 到事件卡片」  
- 「參考 links.md 第 2 項，但要顧 `prefers-reduced-motion`」  

## 注意

- 手勢拖曳／可中斷 spring：可對照 `styles/apple-design/SKILL.md`  
- 純裝飾循環動畫：克制使用，避免干擾閱讀成稿  
- 大檔／影片：本機即可；不必進 git（根目錄已 ignore 多數媒體）  
