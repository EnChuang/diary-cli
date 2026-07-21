# UI 設計討論區

> **用途**：依**使用階段**分開討論／改稿，避免所有畫面攪在一起。  
> **產品規則**仍以 `dev-local/`、`USAGE.md` 為準；本區管「這個階段看起來／點起來如何」。  
> **實作程式**：`ui/`（模板 + `static/style.css`）  
> **風格素材**：`design/styles/`、`motion/`、`references/`  

---

## 怎麼用（提高效率）

1. **只開該階段的檔**討論（例如只談追問 → `03-followup.md`）  
2. 每檔固定區塊：**現況 → 規格鎖定 → 討論中 → 已決 → 待做 → 參考素材**  
3. 跟 AI 說時帶檔名，例如：  
   - 「改 `design/ui-discuss/03-followup.md` 裡討論中的跳過鈕樣式」  
   - 「依 `06-event-read.md` 已決項改模板」  
4. **決了就搬到「已決」**，避免重聊；實作完勾「待做」  

---

## 流程架構總圖

→ **[00-flow.md](./00-flow.md)**（產品 ⟷ CLI ⟷ Web 對照 + mermaid）

---

## 階段索引（對應產品流程）

| 檔案 | 階段 | 路由／入口（現況） | 產品鎖定（摘要） |
|------|------|-------------------|------------------|
| [00-flow.md](./00-flow.md) | **流程總圖** | 全系統 | 對齊檢查 |
| [00-global.md](./00-global.md) | 全站殼、導覽、字色、動效總則 | 全站 | 繁體、本機、克制 |
| [01-home-board.md](./01-home-board.md) | 首頁：歷史榜 + 事件列表 | `GET /` | 榜＝history；列表可進閱讀 |
| [02-new-event.md](./02-new-event.md) | 新增事件（標題 D22 + 主文） | `GET/POST /new` | 手填標題或交 AI |
| [03-followup.md](./03-followup.md) | 追問迴圈 | `/events/{id}/followup` | **跳過**鈕、到此為止（D20） |
| [04-generate.md](./04-generate.md) | 成稿預覽與確認 | `/events/{id}/generate` | 確認兩鈕語意（D19） |
| [05-score.md](./05-score.md) | 評分建議與落盤 | `/events/{id}/score` | 本場 ±10；確認才落盤 |
| [06-event-read.md](./06-event-read.md) | **已落成**事件閱讀 | `GET /events/{id}` | **只**成稿+問答+當次分（D21） |
| [07-characters-merge.md](./07-characters-merge.md) | 人物／merge（UI 尚未做） | CLI 為主 | D18 手動連結 |
| [08-sequel.md](./08-sequel.md) | **事件後續**（UI／CLI 未做） | 閱讀頁「+」 | D23 一父多子、再評分、完成才落庫 |

CLI 對照：`gossip.py`、`board.py` 等 — 行為對齊，**畫面討論以本區 + `ui/` 為主**。

---

## 與其他 design 資料夾

| 路徑 | 關係 |
|------|------|
| `styles/apple-design/` | 動效／材質原則，寫入各階段「參考素材」 |
| `motion/` | 具體 CSS 片段，掛到對應階段檔 |
| `references/` | 截圖；檔名可加前綴 `01-`…`06-` 對階段 |
| **本區 `ui-discuss/`** | **討論結論與待改清單**（工程討論板） |

---

## 變更紀錄

| 日期 | 事件 |
|------|------|
| 2026-07-19 | 建立討論區與各階段模板 |
