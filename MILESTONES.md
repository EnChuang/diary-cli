# 可還原節點（Git 里程碑）

> 改壞了先看這裡。推送後的 **tag** 比「大概某天」可靠。  
> 更新：2026-08-01

---

## 目前建議還原點

| 項目 | 值 |
|------|-----|
| **Tag** | **`v0.2.0`** |
| **Commit** | `2c4b699` |
| **訊息** | milestone v0.2.0: Web main path stable before score calibration |
| **遠端** | https://github.com/EnChuang/diary-cli |
| **Tag 連結** | https://github.com/EnChuang/diary-cli/releases/tag/v0.2.0 |
| **意義** | Web 主路徑穩定版：出場／追問／生成／調分評語／刪除／wipe／觀感分 skill 初版；**評分校準 C1 之前** |

### 還原指令（本機）

```powershell
cd C:\DATA\A_Developement\Project\diary-cli
git fetch origin --tags

# 只看／暫時切到里程碑（detached HEAD，安全試）
git checkout v0.2.0

# 回到最新 main
git checkout main

# 若確定要讓 main 硬回到該點（會丟未推送修改，慎用）
# git checkout main
# git reset --hard v0.2.0
# git push --force   # 僅在你清楚後果時
```

### 還原後注意

- **`data/`、`.env`、`dev-local/` 不在 tag 裡**（本機資料與 Key 仍在你電腦）  
- 還原的是**程式與文件**，不會自動清空你的事件 jsonl  

---

## 歷史節點（之後可追加）

| Tag | Commit | 日期 | 一句話 |
|-----|--------|------|--------|
| `v0.2.0` | `2c4b699` | 2026-08-01 | Web 主路徑 + 刪除／評語／評分防誤判；C1 前安全點 |
| （更早） | `9427bae` | — | Yes Log 品牌、暗色、榜卡片（無 v0.2 功能全集） |

新增里程碑時：打 tag → `git push origin <tag>` → **在本表加一列**。
