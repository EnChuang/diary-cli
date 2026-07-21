# 風格筆記

## 一句話風格

淺色、克制、紅橙主色：清楚層級、少裝飾、閱讀優先。材質參考 apple-design，色票用指定組。

## 全站色票（00-global · 使用者指定）

| 用途 | 變數 | 色碼 |
|------|------|------|
| 主色／按鈕 | primary-100 | `#c21d03` |
| 主色 hover | primary-200 | `#fd5732` |
| 軟強調 | primary-300 | `#ffb787` |
| 中性深 | accent-100 | `#393939` |
| 中性淺 | accent-200 | `#bebebe` |
| 主文字 | text-100 | `#232121` |
| 次文字 | text-200 | `#4b4848` |
| 頁背景 | bg-100 | `#fbfbfb` |
| 升高底 | bg-200 | `#f1f1f1` |
| 邊線 | bg-300 | `#c8c8c8` |
| 卡片 | （白） | `#ffffff` |
| 正分（語意） | ok | `#2a7a3b` |

## 01 首頁（列表）

| 元素 | 處理 |
|------|------|
| 榜 #1 | primary-100 圓標 |
| 榜 #2 | accent-100 灰 |
| 榜 #3 | primary-300 暖銅 |
| 分數正負 | 綠 ok／主色 danger |
| 草稿徽章 | primary-300 底 + 琥珀字 |
| 後續徽章 | primary 淡底 |

## CSS 元件庫（已用）

| ID | 說明 | 路徑 |
|----|------|------|
| `segmented-pill-tabs` | 頂欄 首頁／新增 滑動 pill | `motion/snippets/segmented-pill-tabs.md` |
| `slide-to-unlock` | 進站防窺 · 滑動解鎖 + **Liquid Glass 框** | `motion/snippets/slide-to-unlock.md` |
| `glass-panel` / `liquid-glass` | 解鎖框 Liquid Glass（SVG 折射） | `motion/snippets/liquid-glass-panel.md` |
| `ai-button-spinner` | AI 送出轉圈 | `motion/snippets/ai-button-spinner.md` |
| `score-stepper` | 評分 ± 步進 | `motion/snippets/score-stepper.md` |

## 喜歡

- 系統字、按壓即回饋  
- 半透明頂欄  
- 這組暖紅＋淺灰  
- 分段控制 pill 滑動  

## 不要

- 過多霓虹／雜訊背景  
- 搶戲的無限循環動畫  

## 參考

- `design/styles/apple-design/SKILL.md`  
- 討論：`design/ui-discuss/00-global.md` · `01-home-board.md`  
