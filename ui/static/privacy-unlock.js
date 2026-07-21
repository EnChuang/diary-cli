/**
 * 防窺解鎖：iOS 風格 slide-to-unlock
 * 元件庫：design/motion/snippets/slide-to-unlock.md
 * 僅主畫面：
 *  - reload → 需再解鎖
 *  - 站內導覽回首頁 → sessionStorage 記住，不解鎖
 */
(function () {
  const STORAGE_KEY = "diary-cli-unlocked";
  const THRESHOLD = 0.85;
  const reduce =
    typeof matchMedia === "function" &&
    matchMedia("(prefers-reduced-motion: reduce)").matches;

  const gate = document.querySelector("[data-privacy-gate]");
  if (!gate) return;

  // 已在同 session 解鎖且非重整：直接略過
  try {
    if (
      document.documentElement.classList.contains("privacy-skip") ||
      sessionStorage.getItem(STORAGE_KEY) === "1"
    ) {
      gate.remove();
      document.documentElement.classList.remove("privacy-pending");
      document.documentElement.classList.add("privacy-skip");
      return;
    }
  } catch (_) {
    /* private mode 等：仍顯示閘 */
  }

  document.documentElement.classList.add("privacy-pending");
  gate.setAttribute("aria-hidden", "false");

  const track = gate.querySelector("[data-unlock-track]");
  const thumb = gate.querySelector("[data-unlock-thumb]");
  const fill = gate.querySelector("[data-unlock-fill]");
  if (!track || !thumb || !fill) return;

  let maxX = 0;
  let inset = 4;
  let startX = 0;
  let originX = 0;
  let dragging = false;
  let unlocked = false;
  let currentX = 0;
  let raf = 0;
  let pendingX = null;

  function measure() {
    inset = 4;
    maxX = Math.max(0, track.clientWidth - inset * 2 - thumb.offsetWidth);
  }

  function applyPos(x, animate) {
    const clamped = Math.max(0, Math.min(maxX, x));
    currentX = clamped;

    if (!animate) {
      thumb.style.transition = "none";
      fill.style.transition = "none";
    } else {
      thumb.style.transition = "";
      fill.style.transition = "";
    }

    thumb.style.left = inset + clamped + "px";

    // 綠膠囊：包住白鈕；滑滿 100%（圓頭由 border-radius + track overflow）
    if (maxX > 0 && clamped >= maxX - 0.5) {
      fill.style.width = "100%";
    } else {
      const w = inset + clamped + thumb.offsetWidth + inset;
      fill.style.width = Math.min(track.clientWidth, Math.ceil(w + 0.5)) + "px";
    }

    if (!animate) {
      void thumb.offsetWidth;
      thumb.style.transition = "";
      fill.style.transition = "";
    }
    return clamped;
  }

  function schedulePos(x) {
    pendingX = x;
    if (raf) return;
    raf = requestAnimationFrame(function () {
      raf = 0;
      if (pendingX == null) return;
      const v = pendingX;
      pendingX = null;
      applyPos(v, false);
    });
  }

  function dismissGate() {
    gate.classList.add("is-out");
    document.documentElement.classList.remove("privacy-pending");
    const done = function () {
      gate.remove();
    };
    if (reduce) {
      done();
    } else {
      window.setTimeout(done, 320);
    }
  }

  function latchOpen() {
    unlocked = true;
    track.classList.remove("dragging");
    track.classList.add("unlocked");
    applyPos(maxX, true);
    thumb.setAttribute("aria-valuenow", "100");
    try {
      sessionStorage.setItem(STORAGE_KEY, "1");
    } catch (_) {
      /* ignore */
    }
    window.setTimeout(dismissGate, reduce ? 0 : 260);
  }

  function springBack() {
    track.classList.remove("dragging");
    applyPos(0, !reduce);
    thumb.setAttribute("aria-valuenow", "0");
  }

  function onPointerDown(e) {
    if (unlocked) return;
    if (e.button != null && e.button !== 0) return;
    measure();
    dragging = true;
    track.classList.add("dragging");
    startX = e.clientX;
    originX = currentX;
    thumb.setPointerCapture(e.pointerId);
    e.preventDefault();
  }

  function onPointerMove(e) {
    if (!dragging || unlocked) return;
    const x = applyPos(originX + (e.clientX - startX), false);
    // 拖曳中直接寫入（已 transition:none）；rAF 備援高頻
    if (raf) {
      pendingX = x;
    }
    const pct = maxX > 0 ? Math.round((x / maxX) * 100) : 0;
    thumb.setAttribute("aria-valuenow", String(pct));
  }

  function onPointerUp(e) {
    if (!dragging || unlocked) return;
    dragging = false;
    try {
      thumb.releasePointerCapture(e.pointerId);
    } catch (_) {
      /* ignore */
    }
    const ratio = maxX > 0 ? currentX / maxX : 0;
    if (ratio >= THRESHOLD) {
      latchOpen();
    } else {
      springBack();
    }
  }

  // 首幀：量測後靜默定位，避免 transition 造成重整「彈一下」
  function boot() {
    measure();
    applyPos(0, false);
    thumb.setAttribute("aria-valuemin", "0");
    thumb.setAttribute("aria-valuemax", "100");
    thumb.setAttribute("aria-valuenow", "0");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    requestAnimationFrame(boot);
  }

  thumb.addEventListener("pointerdown", onPointerDown);
  thumb.addEventListener("pointermove", onPointerMove);
  thumb.addEventListener("pointerup", onPointerUp);
  thumb.addEventListener("pointercancel", onPointerUp);

  window.addEventListener("resize", function () {
    if (unlocked) return;
    measure();
    applyPos(Math.min(currentX, maxX), false);
  });
})();
