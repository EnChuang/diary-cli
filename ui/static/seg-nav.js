/**
 * Segmented pill tabs — 讀 active 的 offsetLeft/offsetWidth，
 * 以 cubic-bezier(0.65,0,0.35,1) ~0.4s 滑動高亮 pill。
 * 元件庫：design/motion/snippets/segmented-pill-tabs.md
 */
(function () {
  const DURATION_MS = 400;
  const reduce =
    typeof matchMedia === "function" &&
    matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initSeg(root) {
    const pill = root.querySelector("[data-seg-pill]");
    const items = Array.from(root.querySelectorAll("[data-seg-item]"));
    if (!pill || !items.length) return;

    function moveTo(btn, animate) {
      if (!btn) {
        pill.style.opacity = "0";
        return;
      }
      const useAnim = animate && !reduce;
      if (!useAnim) {
        pill.style.transition = "none";
      } else {
        pill.style.transition = "";
      }
      pill.style.opacity = "1";
      pill.style.left = btn.offsetLeft + "px";
      pill.style.width = btn.offsetWidth + "px";
      if (!useAnim) {
        // 強制 reflow 後恢復 transition，供下次點擊動畫
        void pill.offsetWidth;
        pill.style.transition = "";
      }
    }

    function activeItem() {
      return items.find((el) => el.classList.contains("active")) || null;
    }

    moveTo(activeItem(), false);

    window.addEventListener("resize", function () {
      moveTo(activeItem(), false);
    });

    items.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        if (btn.classList.contains("active")) return;
        // 同源導覽：先播 pill，再跳頁（reduced-motion 立即跳）
        const href = btn.getAttribute("href");
        if (!href || href.startsWith("#") || btn.target === "_blank") return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

        e.preventDefault();
        items.forEach(function (el) {
          el.classList.toggle("active", el === btn);
        });
        moveTo(btn, true);

        const go = function () {
          window.location.href = href;
        };
        if (reduce) {
          go();
        } else {
          window.setTimeout(go, DURATION_MS);
        }
      });
    });
  }

  document.querySelectorAll("[data-seg]").forEach(initSeg);
})();
