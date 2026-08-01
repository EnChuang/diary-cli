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
      // FormData 不含被點的 submit 按鈕；e.submitter 在 Enter／部分瀏覽器可能為空
      var who =
        submitter && submitter.name
          ? submitter
          : btn && btn.name
            ? btn
            : null;
      if (who && who.name) {
        fd.set(who.name, who.value || "on");
      }
      // 追問等表單：後端需要 action；缺了會 422
      if (!fd.has("action")) {
        var actBtn =
          (submitter &&
            submitter.name === "action" &&
            submitter) ||
          form.querySelector('button[type="submit"][name="action"]') ||
          btn;
        if (actBtn && actBtn.name === "action") {
          fd.set("action", actBtn.value || "answer");
        } else {
          fd.set("action", "answer");
        }
      }

      // 注意：表單若有 name="action" 的按鈕，form.action 會被蓋成元素／值（非 URL）
      // 必須用 getAttribute，否則 fetch 會打到 /events/.../answer → 404
      var postUrl =
        form.getAttribute("action") || form.getAttribute("data-action") || "";
      if (!postUrl) {
        unlockForm(form);
        showInlineError(form, "表單缺少送出網址，請重新整理後再試。");
        return;
      }
      var method = (
        form.getAttribute("method") ||
        form.method ||
        "POST"
      ).toUpperCase();

      fetch(postUrl, {
        method: method,
        body: fd,
        credentials: "same-origin",
        redirect: "follow",
        headers: { Accept: "text/html" },
      })
        .then(function (res) {
          // 成功：導向最終 URL（redirect follow 後）或整頁替換 HTML
          if (res.ok) {
            if (res.redirected && res.url) {
              window.location.href = res.url;
              return null;
            }
            if (res.url && res.url !== window.location.href) {
              // 部分環境 redirected 旗標不準，但最終 URL 已變
              try {
                var finalPath = new URL(res.url, window.location.href).pathname;
                var here = window.location.pathname;
                if (finalPath !== here) {
                  window.location.href = res.url;
                  return null;
                }
              } catch (err) {
                /* ignore */
              }
            }
            return res.text().then(function (html) {
              document.open();
              document.write(html);
              document.close();
            });
          }
          return res.text().then(function (html) {
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
