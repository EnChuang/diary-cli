/**
 * 表單送出時：主按鈕改 spinner（data-ai-form / data-ai-submit）
 * AI 長請求：用 fetch 接結果，避免連線被重載掐斷後畫面卡死無提示
 */
(function () {
  function unlockForm(form) {
    form.style.pointerEvents = "";
    form.classList.remove("is-submitting");
    form.querySelectorAll("button").forEach(function (b) {
      b.disabled = false;
      b.classList.remove("is-loading");
      b.removeAttribute("aria-busy");
    });
    var ov = document.getElementById("ai-wait-overlay");
    if (ov) ov.remove();
  }

  function lockForm(form, btn) {
    btn.classList.add("is-loading");
    btn.setAttribute("aria-busy", "true");
    form.classList.add("is-submitting");
    form.querySelectorAll("button").forEach(function (b) {
      if (b !== btn) b.disabled = true;
    });
    form.style.pointerEvents = "none";

    if (!document.getElementById("ai-wait-overlay")) {
      var ov = document.createElement("div");
      ov.id = "ai-wait-overlay";
      ov.className = "ai-wait-overlay";
      ov.innerHTML =
        '<div class="ai-wait-panel">' +
        '<div class="spinner ai-wait-spinner" aria-hidden="true"></div>' +
        "<p class=\"ai-wait-title\">AI 處理中</p>" +
        "<p class=\"ai-wait-hint\">可能需數十秒，請勿關閉此頁。<br/>若完成後仍停在此頁，請按重新整理。</p>" +
        "</div>";
      document.body.appendChild(ov);
    }
  }

  function showInlineError(form, msg) {
    var box = form.closest(".wrap") || document.body;
    var old = box.querySelector(".error.ai-fetch-error");
    if (old) old.remove();
    var el = document.createElement("div");
    el.className = "error ai-fetch-error";
    el.setAttribute("role", "alert");
    el.textContent = msg;
    var card = form.closest(".card") || form;
    card.parentNode.insertBefore(el, card);
  }

  document.querySelectorAll("form[data-ai-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      var submitter = e.submitter;
      var btn =
        submitter && submitter.matches && submitter.matches("[data-ai-submit]")
          ? submitter
          : form.querySelector("[data-ai-submit]");
      if (!btn) return;
      if (
        submitter &&
        submitter !== btn &&
        !submitter.matches("[data-ai-submit]")
      ) {
        return;
      }

      // 長 AI 請求：fetch 可控錯誤；短表單仍可走原生（無 data-ai-fetch 時）
      if (form.getAttribute("data-ai-fetch") === "0") {
        lockForm(form, btn);
        return;
      }

      e.preventDefault();
      lockForm(form, btn);

      var fd = new FormData(form);
      if (submitter && submitter.name) {
        fd.set(submitter.name, submitter.value || "on");
      }

      fetch(form.action, {
        method: (form.method || "POST").toUpperCase(),
        body: fd,
        credentials: "same-origin",
        redirect: "follow",
        headers: { Accept: "text/html" },
      })
        .then(function (res) {
          // follow 後最終 URL（成稿頁或錯誤頁）
          if (res.redirected || res.url) {
            // 成功導向結果頁
            if (res.ok || res.status === 0) {
              window.location.href = res.url;
              return null;
            }
          }
          if (res.ok) {
            return res.text().then(function (html) {
              // 以伺服器 HTML 整頁替換（含錯誤訊息）
              document.open();
              document.write(html);
              document.close();
            });
          }
          return res.text().then(function (html) {
            // 500：若 body 是完整頁就替換，否則顯示摘要
            if (html && html.indexOf("<html") !== -1) {
              document.open();
              document.write(html);
              document.close();
              return;
            }
            unlockForm(form);
            showInlineError(
              form,
              "AI 請求失敗（HTTP " +
                res.status +
                "）。請重新整理後再試；若其實已生成，重新整理即可看到成稿。"
            );
          });
        })
        .catch(function () {
          unlockForm(form);
          showInlineError(
            form,
            "連線中斷（常見原因：伺服器熱重載寫入 data/ 時重啟）。請重新整理本頁——若生成已完成會直接進入成稿與評分。"
          );
        });
    });
  });

  window.addEventListener("pageshow", function () {
    document.querySelectorAll("form[data-ai-form]").forEach(unlockForm);
  });
})();
