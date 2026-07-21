# Segmented pill tabs（滑動分段控制）

> **元件庫 ID**：`segmented-pill-tabs`  
> **實作**：`ui/templates/base.html` · `ui/static/style.css`（`.seg*`）· `ui/static/seg-nav.js`  
> **用在**：頂欄「首頁 / 新增」

---

## Prompt（原始）

```text
Build a segmented tab control where a highlighted pill slides between tabs.
On click, read the target button's offsetLeft and offsetWidth and animate the
pill's left and width to match with cubic-bezier(0.65,0,0.35,1) over ~0.4s;
the active label color crossfades as the pill arrives.
```

---

## CSS 核心

```css
.seg {
  position: relative;
  display: inline-flex;
  padding: 0.2rem;
  border-radius: 999px;
  /* track 底色依主題 */
}

.seg-pill {
  position: absolute;
  top: 0.2rem;
  bottom: 0.2rem;
  left: 0;
  width: 0;
  z-index: 0;
  border-radius: 999px;
  pointer-events: none;
  transition:
    left 0.4s cubic-bezier(0.65, 0, 0.35, 1),
    width 0.4s cubic-bezier(0.65, 0, 0.35, 1);
}

.seg-item {
  position: relative;
  z-index: 1;
  transition: color 0.4s cubic-bezier(0.65, 0, 0.35, 1);
}

.seg-item.active {
  /* 對比色：pill 上文字 */
  color: #fff;
}
```

本站色：pill = `var(--primary-100)`；track = `var(--bg-200)`。

---

## JS 要點

```js
// 點擊／初次 layout：
pill.style.left = btn.offsetLeft + "px";
pill.style.width = btn.offsetWidth + "px";

// 初次定位：先 transition:none，避免載入時飛入
// 全頁導覽：可先播 0.4s 再 location.href（prefers-reduced-motion 則立即跳）
// resize 時重算 active 的 left/width
```

---

## 標記結構

```html
<nav class="seg" data-seg>
  <span class="seg-pill" data-seg-pill aria-hidden="true"></span>
  <a class="seg-item active" data-seg-item href="/">首頁</a>
  <a class="seg-item" data-seg-item href="/new">新增</a>
</nav>
```

---

## 可及性

- `prefers-reduced-motion: reduce`：取消滑動時長、立即換頁  
- 導覽保留真實 `href`（可中鍵／Ctrl 開新分頁）  
- 容器建議 `aria-label`

---

## 複用

其他畫面要同樣控制：複製結構 + 引入 `seg-nav.js`（已 `querySelectorAll('[data-seg]')`），或只引用本檔 CSS 並自管 JS。
