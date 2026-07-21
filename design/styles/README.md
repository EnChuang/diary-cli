# 風格 Skill／設計指南

> 總規範與素材清冊：上一層 [`../README.md`](../README.md)

每個子資料夾 = 一種風格或設計語言，方便之後並存多套。

## 命名

```text
design/styles/<簡短英文名>/
  SKILL.md          ← 主要說明（別人寫的 skill 也可）
  notes.md          ← 可選：你的補充（要用到哪、哪些先忽略）
  extras/           ← 可選：附圖、連結列表
```

例：

| 資料夾 | 用途 |
|--------|------|
| `apple-design/` | Apple 流體介面／材質／動效原則（已放） |
| `minimal-dark/` | 若你之後丟極簡深色指南 |
| `magazine/` | 若你喜歡雜誌排版感 |

**資料夾名請用英文小寫 + 連字號**，不要覆蓋別人的檔名都叫 `SKILL.md` 卻都堆在 `references/`。

## 給 AI 時怎麼說

- 「用 `design/styles/apple-design` 調 UI」  
- 「對照 apple-design，但背景跟 `design/references/xxx.png`」  

不必整份貼進聊天；路徑講清楚即可。
