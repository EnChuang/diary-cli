# 流程架構對照（產品 ⟷ CLI ⟷ Web UI）

> 更新：2026-07-19（含 D23 後續 + **草稿可存／再開詢問**）

---

## 1. 主路徑 + 後續 + 草稿

```mermaid
flowchart TD
  Start([開啟 App/Web]) --> Home[主畫面／歷史榜]
  Note1[冷啟動不彈草稿詢問]
  Start -.-> Note1
  Home --> NewBtn[點 新增事件]
  Home --> Read[點已落成 D21]
  Read --> Plus[點 後續 +]
  NewBtn --> DraftQ1{已有唯一草稿?}
  Plus --> DraftQ2{已有唯一草稿?}
  DraftQ1 -->|繼續寫| Resume[進入該草稿中段]
  DraftQ1 -->|放棄| Del1[刪除唯一草稿] --> S1New[S1 全新]
  DraftQ1 -->|無| S1New
  DraftQ2 -->|繼續寫| Resume
  DraftQ2 -->|放棄| Del2[刪除唯一草稿] --> S1Seq[S1 後續]
  DraftQ2 -->|無| S1Seq
  S1Seq --> Mem[AI 回憶父篇成稿+問答+分]
  S1New --> Draft[S2 初稿 可存 draft]
  Mem --> Draft
  Resume --> Mid[S2/S3/S5/S6 視進度]
  Draft --> Follow[S3 追問 可存]
  Follow --> Gen[S5 成稿 可存]
  Gen --> Score[S6 評分]
  Score --> Conf{確認落盤?}
  Conf -->|是| S7[confirmed + ledger]
  Conf -->|否| StayDraft[維持草稿 可稍後繼續]
  S7 --> Home
  Read --> Nav[子回父 / 父選子含草稿標]
  Mid --> Follow
  Mid --> Gen
  Mid --> Score
```

### 文字版

1. **全庫最多 1 份草稿**；**冷啟動不彈**詢問。  
2. 僅點「新增」或「後續 +」：有草稿 → **繼續寫**／**放棄後開新的**。  
3. 全新／後續可中途存；落盤才進歷史榜。  
4. 後續：銜接+新內容；回憶包；再評分；`續・`。  
5. 閱讀 D21；子回父；父選子。  
6. 第一版：先 Web；不做刪已落成；Merge 仍 CLI。

---

## 2. 三端對照

| 產品 | CLI | Web | 備註 |
|------|-----|-----|------|
| 草稿中途存 | 會寫 events | 會寫 | 與產品一致 |
| 草稿恢復詢問 | 未做 | **待做** | 新增／後續入口 |
| 後續鏈 | 未做 | 未做 | D23 |
| 主路徑 S1–S7 | ✅ | ✅ 起步 | |
| D21 | board 較雜 | 三塊 ✅ | |
| Merge | ✅ | 未做 | |

---

## 3. 對齊結論

主流程一致；**草稿可存 + 詢問繼續／放棄** 與「長文不能重打」一致且**可行**。  
後續鏈與詢問框 **待實作**。
