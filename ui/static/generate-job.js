/**
 * AI 生成：背景任務 + 輪詢，避免長 POST 卡死
 */
(function () {
  var panel = document.getElementById("generate-panel");
  if (!panel) return;
  var eid = panel.getAttribute("data-event-id");
  if (!eid) return;

  var btn = document.getElementById("btn-ai-generate");
  var wait = document.getElementById("gen-wait");
  var actions = document.getElementById("gen-actions");
  var titleEl = document.getElementById("gen-wait-title");
  var hintEl = document.getElementById("gen-wait-hint");
  var errEl = document.getElementById("gen-error");
  var pollTimer = null;

  function showWait(phase) {
    if (wait) wait.classList.remove("is-hidden");
    if (actions) actions.classList.add("is-hidden");
    if (btn) btn.classList.add("is-loading");
    if (titleEl) titleEl.textContent = "AI 處理中";
    if (hintEl) {
      hintEl.innerHTML =
        (phase === "score"
          ? "成稿完成，正在評分…"
          : "正在生成成稿…") +
        "<br/>請勿關閉此頁，完成後會自動進入成稿與評分。";
    }
  }

  function showIdle() {
    if (wait) wait.classList.add("is-hidden");
    if (actions) actions.classList.remove("is-hidden");
    if (btn) {
      btn.classList.remove("is-loading");
      btn.disabled = false;
    }
  }

  function showError(msg) {
    showIdle();
    if (!errEl) return;
    errEl.textContent = msg || "生成失敗";
    errEl.classList.remove("is-hidden");
  }

  function goResult() {
    window.location.href = "/events/" + encodeURIComponent(eid) + "/generate";
  }

  function poll() {
    fetch("/events/" + encodeURIComponent(eid) + "/generate/status", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.phase) showWait(data.phase);

        if (data.has_story || data.status === "done") {
          if (pollTimer) clearInterval(pollTimer);
          goResult();
          return;
        }
        if (data.status === "error") {
          if (pollTimer) clearInterval(pollTimer);
          showError(data.error || "生成失敗，請稍後再試。");
          return;
        }
        if (data.running || data.status === "running") {
          showWait(data.phase || "generate");
        }
      })
      .catch(function () {
        // 短暫網路抖動：繼續輪詢
      });
  }

  function start() {
    if (errEl) {
      errEl.classList.add("is-hidden");
      errEl.textContent = "";
    }
    showWait("generate");
    if (btn) btn.disabled = true;

    var force =
      /[?&]fresh=1(?:&|$)/.test(window.location.search) ||
      /[?&]force=1(?:&|$)/.test(window.location.search);
    var startUrl =
      "/events/" +
      encodeURIComponent(eid) +
      "/generate/start" +
      (force ? "?force=1" : "");

    fetch(startUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data.has_story || data.status === "done") {
          goResult();
          return;
        }
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 1500);
        poll();
      })
      .catch(function (e) {
        showError(
          "無法啟動生成：" +
            (e && e.message ? e.message : "未知錯誤") +
            "。請重新整理後再試。"
        );
      });
  }

  if (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      start();
    });
  }

  // 頁面載入時若已在跑，繼續輪詢
  if (wait && !wait.classList.contains("is-hidden")) {
    pollTimer = setInterval(poll, 1500);
    poll();
  }
})();
