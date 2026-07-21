/**
 * 亮／暗主題切換 · localStorage: yeslog-theme = light | dark
 */
(function () {
  var KEY = "yeslog-theme";
  var root = document.documentElement;
  var btn = document.querySelector("[data-theme-toggle]");
  var meta = document.getElementById("meta-theme-color");

  function current() {
    var t = root.getAttribute("data-theme");
    return t === "dark" ? "dark" : "light";
  }

  function apply(theme) {
    var t = theme === "dark" ? "dark" : "light";
    root.setAttribute("data-theme", t);
    try {
      localStorage.setItem(KEY, t);
    } catch (e) {}
    if (meta) {
      meta.setAttribute("content", t === "dark" ? "#1A1F2B" : "#fbfbfb");
    }
    if (btn) {
      btn.setAttribute(
        "aria-label",
        t === "dark" ? "切換為亮色模式" : "切換為暗色模式"
      );
      btn.title = t === "dark" ? "亮色模式" : "暗色模式";
    }
  }

  // 與 head 腳本對齊
  apply(current());

  if (btn) {
    btn.addEventListener("click", function () {
      apply(current() === "dark" ? "light" : "dark");
    });
  }
})();
