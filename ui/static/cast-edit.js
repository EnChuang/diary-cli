/**
 * 確認出場：動態新增列、更新 count
 */
(function () {
  var list = document.getElementById("cast-list");
  var countIn = document.getElementById("cast-count");
  var addBtn = document.getElementById("cast-add");
  var tpl = document.getElementById("cast-row-tpl");
  if (!list || !countIn || !addBtn || !tpl) return;

  function reindex() {
    var rows = list.querySelectorAll("[data-cast-row]");
    rows.forEach(function (row, i) {
      row.querySelectorAll("input").forEach(function (inp) {
        var n = inp.getAttribute("name") || "";
        if (n.indexOf("name_") === 0) inp.setAttribute("name", "name_" + i);
        else if (n.indexOf("user_") === 0) inp.setAttribute("name", "user_" + i);
        else if (n.indexOf("drop_") === 0) inp.setAttribute("name", "drop_" + i);
      });
    });
    countIn.value = String(rows.length);
  }

  addBtn.addEventListener("click", function () {
    var html = tpl.innerHTML.replace(/IDX/g, "0");
    var wrap = document.createElement("div");
    wrap.innerHTML = html.trim();
    var row = wrap.firstElementChild;
    if (row) list.appendChild(row);
    reindex();
    var last = list.querySelector("[data-cast-row]:last-child input[type=text]");
    if (last) last.focus();
  });

  reindex();
})();
