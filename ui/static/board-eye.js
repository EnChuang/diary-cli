/**
 * 歷史榜：單一眼睛切換全名
 * 初始一律隱藏（* 取代）；不讀取上次「顯示」狀態，避免進站就露出真名
 */
(function () {
  var root = document.querySelector("[data-board]");
  if (!root) return;
  var btn = root.querySelector("[data-eye-toggle]");
  var list = root.querySelector("[data-rank-list]");
  if (!btn || !list) return;

  var names = list.querySelectorAll("[data-full-name]");

  function mask(text) {
    var s = String(text || "");
    if (!s) return "";
    return Array.from(s)
      .map(function () {
        return "*";
      })
      .join("");
  }

  function apply(show) {
    list.classList.toggle("show-full-names", show);
    btn.setAttribute("aria-pressed", show ? "true" : "false");
    btn.setAttribute("aria-label", show ? "隱藏全名" : "顯示全名");
    btn.title = show ? "隱藏全名" : "顯示全名";

    names.forEach(function (el) {
      var real = el.getAttribute("data-real-name") || "";
      if (!real) return;
      el.textContent = show ? real : mask(real);
    });
  }

  // 初始：一定隱藏（HTML 已是 *；再強制一次）
  apply(false);

  btn.addEventListener("click", function () {
    apply(!list.classList.contains("show-full-names"));
  });
})();
