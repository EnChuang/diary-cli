# Liquid Glass 解鎖框

> **元件庫 ID**：`liquid-glass-panel`  
> **參考**：[iyinchao/liquid-glass-studio](https://github.com/iyinchao/liquid-glass-studio)（完整版為 WebGL2/WebGPU）  
> **本專案**：CSS + SVG `feDisplacementMap` 近似折射／霧化，不引入 WebGL 依賴  

## 結構

```html
<svg class="lg-svg-defs">… filter#lg-panel / #lg-track …</svg>
<div class="privacy-panel liquid-glass">
  <span class="lg-specular"></span>
  <span class="lg-rim"></span>
  <div class="lg-inner">…</div>
</div>
```

## 要點

| 效果 | 作法 |
|------|------|
| 折射 | Chromium：`backdrop-filter: url(#lg-panel)`（feTurbulence + feDisplacementMap + blur） |
| Fallback | `blur + saturate + 半透明漸層`（Safari / Firefox） |
| Fresnel 高光 | `.lg-specular` 斜向掃光 |
| 邊緣厚度 | `.lg-rim` 內陰影 |
| 背後場景 | 降透明度但仍可見 + 色光斑 scrim |

## 限制

- SVG-as-backdrop 主要在 **Chromium** 完整；其他瀏覽器走 fallback 仍是霧玻璃。  
- 完整 liquid-glass-studio 的色散／SDF 合體需 WebGL，本機日記 UI 不引入。  
