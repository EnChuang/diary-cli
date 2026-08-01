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
  var abandon = document.getElementById("gen-abandon");
  var pollTimer = null;
  var navigated = false;

  function showWait(phase) {
    if (wait) wait.classList.remove("is-hidden");
    if (actions) actions.classList.add("is-hidden");
    if (abandon) abandon.classList.add("is-hidden");
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
    if (abandon) abandon.classList.remove("is-hidden");
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
    // 只導向一次，避免 has_story 早於評分完成時整頁狂刷
    if (navigated) return;
    navigated = true;
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    window.location.replace(
      "/events/" + encodeURIComponent(eid) + "/generate"
    );
  }

  function isStillRunning(data) {
    return !!(data.running || data.status === "running");
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
        if (data.status === "error") {
          if (pollTimer) clearInterval(pollTimer);
          showError(data.error || "生成失敗，請稍後再試。");
          return;
        }

        // 成稿已寫入但背景仍在評分：只更新文案，禁止 reload
        if (isStillRunning(data)) {
          showWait(data.phase || "generate");
          return;
        }

        // 背景結束後才進成稿／調分頁
        if (data.status === "done" || data.has_story) {
          goResult();
          return;
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
    navigated = false;
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
        // 已完成且未在跑 → 直接看結果；剛啟動則開始輪詢
        if (
          !isStillRunning(data) &&
          (data.status === "done" || data.has_story)
        ) {
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

  // 頁面載入時若已在跑，繼續輪詢（勿因 has_story 提前跳轉）
  if (wait && !wait.classList.contains("is-hidden")) {
    pollTimer = setInterval(poll, 1500);
    poll();
  }
})();
