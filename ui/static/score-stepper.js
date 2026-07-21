/**
 * 評分 ± 步進 + bump 動畫
 * 元件庫：design/motion/snippets/score-stepper.md
 */
(function () {
  function format(n) {
    if (n > 0) return "+" + n;
    return String(n);
  }

  document.querySelectorAll("[data-score-row]").forEach(function (row) {
    var input = row.querySelector("[data-score-input]");
    var valEl = row.querySelector("[data-step-val]");
    if (!input || !valEl) return;

    row.querySelectorAll(".step-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var step = parseInt(btn.getAttribute("data-step") || "0", 10);
        var cur = parseInt(input.value, 10);
        if (isNaN(cur)) cur = 0;
        var next = cur + step;
        // 軟限制顯示；落盤時仍會 clamp
        if (next > 100) next = 100;
        if (next < -100) next = -100;
        input.value = String(next);
        valEl.textContent = format(next);
        valEl.classList.remove("bump");
        void valEl.offsetWidth;
        valEl.classList.add("bump");
      });
    });
  });
})();
