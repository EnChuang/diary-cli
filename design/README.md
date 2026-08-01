# 設計素材與工程紀錄

> **本檔角色**：設計資料夾的**權威說明**（放什麼、怎麼命名、怎麼交給 AI、與 `ui/` 的關係）。  
> **產品進度／下一步**：見 [`dev-local/SESSION.md`](../dev-local/SESSION.md)  
> **使用測試**：見根目錄 [`USAGE.md`](../USAGE.md)  
> **更新日期**：2026-08-01  

---

## 1. 為什麼有這個資料夾

| 目的 | 說明 |
|------|------|
| 風格參考 | 截圖、別人寫的 design skill、CSS 動效，與程式分離 |
| 工程可追溯 | 之後改 UI 知道「對照哪份素材」 |
| 不影響執行 | **沒有** design 也能跑 `ui/`／CLI；有素材時再對稿 |

UI 程式在 **`ui/`**（FastAPI + 模板 + `ui/static/style.css`）。  
定稿視覺時：**先讀本資料夾 → 再改 `ui/static/` 與模板**。

---

## 2. 目錄結構（現況）

```text
design/
├── README.md                 ← 本檔（素材規範 + 工程紀錄）
├── notes.md
├── ui-discuss/               ← 【UI 分階段討論】00～10
│   ├── README.md             ← 階段索引
│   └── 00-global.md …
├── scoring/                  ← 【評分核心】可重現的觀感分標準（計畫／校準／金標）
│   └── 00-score-core-plan.md
├── styles/                   ← 設計語言／Skill（如 apple-design）
├── motion/                   ← CSS／動效
├── references/               ← 截圖
├── palette/
└── typography/
```

**評分哲學／長版 skill 升級**：見 [`scoring/00-score-core-plan.md`](./scoring/00-score-core-plan.md)（執行規則仍在 `skill/story_score.md`）。

**改某個畫面**：開 `ui-discuss/` 對應階段檔討論 → 再改 `ui/`。

---

## 3. 放什麼素材（對照表）

| 素材類型 | 可以嗎 | 路徑 | 命名建議 |
|----------|--------|------|----------|
| 別人寫的 **Skill／設計指南** | ✅ | `styles/<英文短名>/SKILL.md` | 一夾一套；勿全堆在 `references/` |
| 該 skill 的使用備註 | ✅ | `styles/<名>/notes.md` | 寫「要用到哪、先略過什麼」 |
| App／網頁**截圖** | ✅ | `references/` | `01-home.png`、`02-event.png` |
| **CSS 動畫／片段** | ✅ | `motion/snippets/` | `01-card-enter.css` |
| 動畫／文章**連結** | ✅ | `motion/links.md` | 表格列：說明／URL／用在哪 |
| 色票 | ✅ | `palette/` 或 `notes.md` | 可圖可 md |
| 字體偏好 | ✅ | `typography/` 或 `notes.md` | |
| 總偏好一句話 | ✅ | `notes.md` | |
| 整份 skill 貼聊天 | ⚠️ 不必要 | — | 放路徑後跟 AI 說資料夾名即可 |

### 已登錄素材（工程清冊）

| 日期 | 路徑 | 類型 | 備註 |
|------|------|------|------|
| 2026-07-19 | `styles/apple-design/SKILL.md` | 設計 Skill | 原放 `references/SKILL.md`，已改名分夾以便並存多套 |
| 2026-07-19 | `styles/apple-design/notes.md` | 使用備註 | 本專案取「克制／流暢／層級」，非整包 iOS |
| 2026-07-20 | `motion/snippets/segmented-pill-tabs.md` | CSS 元件 | 滑動 pill 分段控制；實作 base 頂欄 + `seg-nav.js` |
| 2026-07-20 | `motion/snippets/slide-to-unlock.md` | CSS 元件 | iOS 滑動解鎖 + 防窺打霧；`privacy-unlock.js` |
| 2026-07-20 | `motion/snippets/ai-button-spinner.md` | CSS 元件 | AI 送出轉圈；`ai-loading.js` |
| 2026-07-20 | `motion/snippets/score-stepper.md` | CSS 元件 | 評分 ± 步進 bump |
| （待補） | `references/*` | 截圖 | 使用者自行丟入 |
| （待補） | `motion/links.md` 列 | 連結 | 使用者自行追加 |

**新增素材時**：在上表加一列（日期／路徑／類型／一句備註），方便之後接續。

---

## 4. 第二套、第三套風格怎麼加

1. 建 `design/styles/<新英文名>/`  
2. 放入 `SKILL.md`（必要）與可選 `notes.md`  
3. 更新本檔 **§3 已登錄素材** 一列  
4. 跟 AI 說：「以 `styles/xxx` 為主」或「混 apple-design + references/某圖」

資料夾名：**英文小寫 + 連字號**（例：`minimal-dark`、`magazine`）。

---

## 5. CSS／動畫怎麼給 AI

1. 檔案 → `motion/snippets/序號-用途.css`（或 `.md` 包 code fence）  
2. 或連結 → `motion/links.md`  
3. 指令例：「套用 `motion/snippets/02-card-enter.css` 到事件卡片」  

約束（產品）：

- 閱讀頁以成稿為主，動效**不搶戲**  
- 顧 `prefers-reduced-motion`  
- 手勢／spring 可對照 `styles/apple-design/SKILL.md`  

詳見 [`motion/README.md`](motion/README.md)。

---

## 6. 與產品／UI 的邊界

| 來源 | 管什麼 |
|------|--------|
| `design/ui-discuss/` | **分階段 UI 討論**（已決／待做／參考） |
| `design/styles|motion|references` | 風格素材本體 |
| `dev-local/` + USAGE | 產品規則（D18～D22、±10 等） |
| `ui/` | 實際頁面與 `static/style.css` |

**風格不能蓋掉產品語意**（例如已落成事件仍只顯示：成稿＋問答＋當次分）。

### UI 啟動

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
.\.venv\Scripts\activate
uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765
```

---

## 7. Git 注意

| 可進 git（建議） | 建議不進／已 ignore |
|------------------|---------------------|
| 本 README、`notes.md`、`styles/**/*.md`、`motion/README.md`、`links.md` | 大圖、psd、錄影、`references/*` 媒體、`motion/snippets` 大量二進位 |

根目錄 `.gitignore` 已擋常見圖片／影片；**文字 skill 可保留在庫內**方便 Agent 讀取。

---

## 8. 變更紀錄（設計資料夾本身）

| 日期 | 變更 |
|------|------|
| 2026-07-19 | 初建 `design/`（references／palette／typography／notes） |
| 2026-07-19 | 建 `ui/` 極簡殼；樣式暫中性深色 |
| 2026-07-19 | Apple skill 自 `references/SKILL.md` → `styles/apple-design/` |
| 2026-07-19 | 增 `motion/`；本檔升格為**素材規範 + 工程紀錄** |
| 2026-07-19 | 建 **`ui-discuss/`** 分階段討論區（00～07） |

---

## 9. 給下一棒 Agent 的一句

```text
設計素材只讀 design/（結構見本 README §2～§3）。
改視覺對照 styles/ 與 motion/，改 ui/static 與 templates。
產品規則仍以 SESSION / USAGE / DATA_CONTRACT 為準。
```
