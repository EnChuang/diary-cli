# 10 · 一鍵銷毀（本機重置）

## 規劃

| 項目 | 決議 |
|------|------|
| 入口 | **頁腳** 極淡「**一鍵銷毀**」→ `/settings/wipe` |
| 為何低調 | 破壞性；不進頂欄 |
| 確認 | 點「一鍵銷毀」→ **確認框** →「確認銷毀」才 POST |
| 清空 | characters / events / ledger + pending + gen jobs |
| 保留 | `.env`、程式、主題 localStorage |
| 完成後 | `/?wiped=1`，清 session 解鎖旗標 |

## 實作

- `storage/reset.py` · `wipe_all_local_data`
- `ui/templates/wipe.html` + `wipe-confirm.js`（modal）
- 頁腳：`base.html` `.footer-wipe`
