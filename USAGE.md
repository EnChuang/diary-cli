# 野史錄 · Yes Log — 測試使用說明與規則

> 給**你自己實測**用。產品構想細節見 `dev-local/`（不上傳 Git）。  
> 更新：2026-07-19  
> **開發進度／總體檢／下一步**：`dev-local/SESSION.md`（接續開工必讀）

---

## 1. 目錄（現況）

```text
diary-cli/
├── USAGE.md                 ← 本檔（測試用法與規則）
├── README.md                ← 安裝與快速入口
├── AGENTS.md                ← 給 AI Agent 交接
│
├── gossip.py                ← 【主入口】完整流程
├── story_draft.py           ← 僅初稿
├── story_followup.py        ← 僅追問
├── story_generate.py        ← 僅成稿
├── story_score.py           ← 僅評分／落盤
├── board.py                 ← 榜單與閱讀
│
├── llm_client.py            ← ModelArk 呼叫 + JSON 重試
├── text_zh.py               ← 繁體轉換
│
├── skill/                   ← AI 規則（改文筆改這裡）
│   ├── story_draft.md
│   ├── story_followup.md
│   ├── story_generate.md
│   └── story_score.md
│
├── storage/                 ← 本地讀寫（無 AI）
│   ├── paths.py
│   ├── characters.py
│   ├── events.py
│   ├── ledger.py
│   ├── scoring.py           ← 平均 ±10
│   ├── confirm.py           ← 確認落盤
│   └── merge.py             ← 角色合併
│
├── data/                    ← 你的真實資料（gitignore）
│   ├── characters.jsonl
│   ├── events.jsonl
│   └── score_ledger.jsonl
│
├── dev-local/               ← 構想／契約／進度（gitignore）
├── .env                     ← 金鑰（勿提交）
├── .env.example
└── requirements.txt
```

**已退役（勿再找）**：`main.py`、日記 Skill、`diary.jsonl`。

---

## 2. 第一次準備

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
.\.venv\Scripts\activate
# 若無 venv：
#   python -m venv .venv
#   .\.venv\Scripts\activate
#   pip install -r requirements.txt

# .env 需有 ARK_API_KEY（可從 .env.example 複製）
```

| 變數 | 說明 |
|------|------|
| `ARK_API_KEY` | 必填 |
| `ARK_BASE_URL` | 可選，預設東南亞 BytePlus |
| `ARK_MODEL` | 可選，須在控制台已開通 |

---

## 3. 怎麼測（建議順序）

### 方式 0 — 本機網頁 UI（Phase I 起步）

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
.\.venv\Scripts\activate
uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765 --reload-dir ui --reload-dir storage --reload-dir skill
```

開瀏覽器：`http://127.0.0.1:8765`

| 頁面 | 功能 |
|------|------|
| 首頁 | 歷史榜 + 事件列表（點「觀看」） |
| 新增事件 | 標題手填／交給 AI + 主文 → 初稿 |
| 追問 | 回答 / **跳過** / 到此為止 |
| 成稿／評分 | 預覽確認 → 建議分 → 落盤 |
| 已落成觀看 | **成稿 + 問答 + 此次評分**（D21）；右上角 **+**＝後續 |
| 後續（D23） | 已落成頁按 **+** → 寫新發展（帶父篇回憶）→ 同主流程 → 落盤 |
| 草稿（D24） | 全庫 **1 份**；點「新增」或「後續」時若有草稿 → 繼續／放棄（冷啟動不彈） |

**設計參考（工程紀錄）**：完整規範與素材清冊 → [`design/README.md`](design/README.md)  

| 放什麼 | 路徑 |
|--------|------|
| 風格 Skill（如 Apple） | `design/styles/<名>/SKILL.md` |
| 截圖 | `design/references/` |
| CSS 動畫 | `design/motion/snippets/` 或 `motion/links.md` |
| 你的偏好 | `design/notes.md` |

樣式實作檔：`ui/static/style.css`（中性深色起步，依 design 再調）。  

**分階段 UI 討論**（提高效率）：[`design/ui-discuss/README.md`](design/ui-discuss/README.md)  
例：只改追問 → 開 `design/ui-discuss/03-followup.md` 再改 `ui/`。

### 方式 A — CLI 一條龍

```powershell
python gossip.py
```

1. 貼**主文**，單獨一行 `END`  
2. 看 AI **初稿**  
3. **追問**：回答問題；結束打 `到此為止`  
4. **成稿**：問是否寫入 → 通常 `y`  
5. **評分**：可改分或直接確認落盤 → `y`  
6. 自動印榜單摘要  

少打字版（內建兩輪示範問答，仍會呼叫 AI 做初稿／成稿／評分）：

```powershell
python gossip.py --quick
# 或直接帶主文：
python gossip.py --quick --text "今天……"
```

### 方式 B — 分步

```powershell
python story_followup.py                    # 主文→初稿→追問
python story_generate.py --event evt_xxxx   # 成稿
python story_score.py --event evt_xxxx      # 評分落盤
python board.py rank
```

中斷後恢復：

```powershell
python story_followup.py --event evt_xxxx
python gossip.py --event evt_xxxx
```

### 方式 C — 只看資料

```powershell
python board.py rank              # 歷史榜
python board.py events            # 事件列表
python board.py event evt_xxxx    # 一篇詳情
python board.py char 1            # 榜上第 1 名
python board.py status            # 各檔列數
```

VS Code 也可直接打開 `data/*.jsonl`（一行一筆 JSON）。

---

## 4. 追問時可打的指令（CLI）

| 輸入（整行） | 意思 |
|--------------|------|
| （一般文字） | 回答當題 |
| `跳過` 或 `skip` | 跳過此題（寫入「（跳過）」） |
| `補充: …` | 自由補充 |
| `改前答` | 改上一則你的回答 |
| `到此為止` | **結束追問**（不是跳過單題） |
| `顯示` | 看目前問答 |
| `help` | 說明 |

注意：

- 只有**整行等於** `跳過`／`skip` 才算跳過；「不知道」「先跳過吧」會當**正常回答**存檔。  
- 之後 UI 會做**跳過按鈕**（規劃已鎖定），不必靠記指令。

---

## 5. 產品規則（實測時心裡要有的）

### 5.1 確認才落盤

- AI 出的都是**草稿／建議**。  
- 成稿寫入、評分寫入歷史榜，都要你 **`y` 確認**（未來 UI＝兩個按鈕：確認／取消）。  
- 未確認前可重跑、可取消。

### 5.2 評分

| 規則 | 說明 |
|------|------|
| 誰被評 | **只有非「我」**的登場者 |
| 分數範圍 | 當次 **-100～100** 整數 |
| 同場約束 | 以**這一場**各人當次分算平均 μ，每人須在 **μ±10** 內（再與 ±100 交集） |
| 不是歷史分 | ±10 **不管**榜上歷史總分 |
| 材料 | 主文 + 成稿 + **追問問答**（含你的回答）一起影響 AI 建議分 |
| 你可改 | 落盤前可調分；確認後寫 ledger，歷史分＝ledger 加總 |

### 5.3 角色／名字

| 規則 | 說明 |
|------|------|
| 系統職責 | 標出「有人出現」、建檔、給分對象 |
| 自動同一人 | 僅當名字轉繁體後**相同**才重用 id |
| 不自動做的 | 「垃圾俊傑」≠ 自動等於「林俊傑」 |
| 同一人怎麼連 | **手動 merge**（見下） |
| 成稿暱稱 | 正文可用「小X」；主檔 `display_nick` 不每篇被 AI 覆寫 |

```powershell
python -m storage.merge dupes              # 看同名重複
python -m storage.merge chars <被吃掉> <保留> -y
python -m storage.merge dedupe -y          # 自動合併同名＋名稱轉繁
python -m storage.merge recompute          # 依 ledger 重算歷史分
```

### 5.4 繁體

- 你輸入、模型輸出，進系統前都會**轉成繁體**。  
- Skill 也要求模型用繁體。

### 5.5 隱私與 Git

- `data/*.jsonl`、`.env`、`dev-local/` **不要** commit。  
- 內容會送到 ModelArk（依你的 Key）。

---

## 6. 示範主文（可整段貼）

```text
今天午餐時陳美玲跟王大明在茶水間吵起來。
小美說上次提案是她做的，大明卻在會上搶功。
林主管經過只說「私下解決」，兩邊更不爽。
我在旁邊不敢插話，只覺得這週例會氣氛會很糟。
END
```

### 預期大致結果（細節每次 AI 會不同）

| 階段 | 預期 |
|------|------|
| 初稿 | 有標題、標籤、可讀正文；登場含小美／大明／主管／我 |
| 追問 | 一次一題；你的答會進問答 |
| 成稿 | 正文用暱稱、有對話；尚不改歷史榜 |
| 評分 | 我不進分；小美偏正、大明偏負較常見；分數過 ±10 會被收斂 |
| 落盤後 | `status=confirmed`；`board.py rank` 看得到人 |

---

## 7. 常見問題

**Q：rank 出現兩個同名？**  
舊測試或簡繁曾分裂。執行：`python -m storage.merge dedupe -y`

**Q：清空所有八卦資料重測？**  
刪除或清空 `data/events.jsonl`、`data/score_ledger.jsonl`，`characters.jsonl` 可只留 `self`（或整檔重來後跑任意流程會再建）。勿提交這些檔。

**Q：改 AI 口氣？**  
改 `skill/` 裡對應的 `.md`，不要先改模型名。

**Q：diary.jsonl？**  
已移除，不再使用。

---

## 8. 之後 UI（暫定，尚未做畫面）

| 場景 | 規劃 |
|------|------|
| 確認寫入 | 兩個按鈕：確認／取消 |
| 追問 | 必有 **跳過** 按鈕 |
| **點選已落成事件** | 只看三塊：**完整成稿故事**、**AI／你的問答**、**此次評分**（不含主文／初稿／ledger 明細，暫定） |
| **新增事件標題（D22）✅ CLI** | 可先填標題；或 **交給 AI**（成稿時依完整故事取名）。手填則成稿**強制用你的標題** |

```powershell
# 互動：會先問標題（Enter＝交給 AI）
python gossip.py

# 手填標題
python gossip.py --title "茶水間風波"
python story_followup.py --title "茶水間風波"

# 明確交給 AI
python gossip.py --title-ai
python gossip.py --quick --title-ai
```

CLI 觀看：`python board.py event <id>`（會標示手填／延後標題）。

---

## 9. 與開發文件的分工

| 檔案 | 給誰 |
|------|------|
| **USAGE.md（本檔）** | 你：怎麼測、有哪些規則 |
| **README.md** | 安裝與最短入口 |
| **AGENTS.md** | AI 開工交接 |
| **dev-local/** | 構想、契約、進度（本機） |
