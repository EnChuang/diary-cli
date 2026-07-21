# 04 · 成稿預覽與確認

## 現況（程式）

- 路由：`GET/POST /events/{id}/generate`  
- 模板：`ui/templates/generate.html`  
- 操作：AI 生成預覽 → **確認寫入**／重新生成  
- 預覽暫存：`data/.pending_generate_{id}.json`  

## 規格鎖定（D19、D22）

- 確認語意＝兩路：**寫入**／**取消或重來**（勿靠打字 y/N）  
- 標題：延後則 AI 產；手填則強制 `user_title`  
- 此步**不**寫歷史分、不 confirm 事件  

## 討論中

- 

## 已決

| 日期 | 決議 | 備註 |
|------|------|------|
| | | |

## 待做（實作）

- [ ] 預覽版面＝接近 D21 閱讀體驗  
- [ ] 長文閱讀舒適度（行寬、字級）  

## 參考素材

- styles：  
- motion：  
- references：`04-generate-*.png`  
