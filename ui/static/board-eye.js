/**
 * 歷史榜：單一眼睛切換全名；隱藏時以 * 取代
 */
(function () {
  var root = document.querySelector("[data-board]");
  if (!root) return;
  var btn = root.querySelector("[data-eye-toggle]");
  var list = root.querySelector("[data-rank-list]");
  if (!btn || !list) return;

  var KEY = "diary-cli-board-show-names";
  var names = list.querySelectorAll("[data-full-name]");

  function mask(text) {
    var s = String(text || "");
    if (!s) return "";
    // 全形／中文也一碼一星
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
      var real = el.getAttribute("data-real-name") || el.textContent || "";
      el.textContent = show ? real : mask(real);
    });

    try {
      sessionStorage.setItem(KEY, show ? "1" : "0");
    } catch (e) {}
  }

  var initial = false;
  try {
    initial = sessionStorage.getItem(KEY) === "1";
  } catch (e) {}
  apply(initial);

  btn.addEventListener("click", function () {
    apply(!list.classList.contains("show-full-names"));
  });
})();
