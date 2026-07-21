# Slide-to-unlock（iOS 風格滑動解鎖）

> **元件庫 ID**：`slide-to-unlock`  
> **實作**：`ui/templates/base.html`（`.privacy-gate`）· `ui/static/style.css` · `ui/static/privacy-unlock.js`  
> **用在**：全站防窺閘；解鎖後才可操作主畫面內容  

---

## Prompt（原始）

```text
Build an iOS-style slide-to-unlock control. A round thumb sits at the left of a
pill track; dragging moves it 1:1 with the pointer (disable the transition while
dragging) and a green fill grows behind it. On release, if the thumb passed ~85%
of the track, latch it open at the far end and mark it unlocked; otherwise spring
it back to the start with a cubic-bezier(0.34, 1.56, 0.64, 1).
```

---

## CSS 核心

```css
.unlock-thumb {
  transition: left 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.unlock-track.dragging .unlock-thumb {
  transition: none; /* follow finger 1:1 */
}
.unlock-track.unlocked .unlock-thumb {
  background: #4cd08a;
}
```

防窺層（Liquid Glass）：

- `html.privacy-pending` → 主內容降透明度 + `pointer-events: none`（不整頁 blur）
- `.privacy-scrim` → 淡色漸層 + `backdrop-filter: blur`
- `.privacy-panel.glass-panel` → 半透明白玻璃、頂緣高光、柔影
- `.unlock-track` / `.unlock-thumb` → 玻璃槽 + 白玻璃球拇指
- `prefers-reduced-transparency` → 退回實心白卡
- 解鎖後移除 class，閘門 fade out

---

## JS 要點

```js
// 拖曳：setPointerCapture；left = clamp(origin + dx, 0, maxX)
// maxX = trackWidth - padding - thumbWidth
// 放開：ratio >= 0.85 → latch + unlocked；否則 left=0（spring）
// 解鎖後 sessionStorage['diary-cli-unlocked']='1'
// reload 時 head script 清掉 → 再解鎖；navigate 回首頁則略過
```

---

## 標記結構

```html
<div class="privacy-gate" data-privacy-gate>
  <div class="privacy-scrim"></div>
  <div class="privacy-panel">
    …
    <div class="unlock-track" data-unlock-track>
      <div class="unlock-fill" data-unlock-fill></div>
      <span class="unlock-label">滑動解鎖</span>
      <button type="button" class="unlock-thumb" data-unlock-thumb role="slider"></button>
    </div>
  </div>
</div>
```

---

## 產品決策（本專案）

| 項目 | 決議 |
|------|------|
| 範圍 | **僅主畫面**（`page == 'home'` / `GET /`） |
| 記住 | `sessionStorage['diary-cli-unlocked']` |
| 重新整理首頁 | `navigation.type === 'reload'` → 清旗標 → **再解鎖** |
| 站內導回首頁 | 旗標仍在 → **不解鎖**（例：新增 → 首頁） |
| 其他頁 | 新增／事件等**無**閘門 |
| 門檻 | 85% 軌道 |
| 解鎖色 | `#4cd08a`（prompt 指定） |

---

## 可及性

- `role="dialog"` + `aria-modal`
- thumb `role="slider"` + valuemin/max/now  
- `prefers-reduced-motion`：縮短動畫；`reduced-transparency`：Scrim 更實、少 blur  
