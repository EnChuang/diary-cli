/**
 * 一鍵銷毀：
 * - 無資料 → 提示「目前已清空」
 * - 有資料 → 確認框後才送出
 */
(function () {
  var openBtn = document.querySelector("[data-open-wipe]");
  var destroyModal = document.getElementById("wipe-modal");
  var emptyModal = document.getElementById("wipe-empty-modal");
  if (!openBtn) return;

  var alreadyEmpty =
    emptyModal && emptyModal.getAttribute("data-already-empty") === "1";

  function openModal(el) {
    if (!el) return;
    el.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal(el) {
    if (!el) return;
    el.hidden = true;
    document.body.style.overflow = "";
  }

  openBtn.addEventListener("click", function () {
    if (alreadyEmpty) {
      openModal(emptyModal);
      return;
    }
    openModal(destroyModal);
  });

  if (destroyModal) {
    destroyModal.querySelectorAll("[data-close-wipe]").forEach(function (el) {
      el.addEventListener("click", function () {
        closeModal(destroyModal);
        openBtn.focus();
      });
    });
  }

  if (emptyModal) {
    emptyModal.querySelectorAll("[data-close-empty]").forEach(function (el) {
      el.addEventListener("click", function () {
        closeModal(emptyModal);
        openBtn.focus();
      });
    });
    // 若伺服器標記 show_empty_hint，載入時就顯示
    if (!emptyModal.hidden) {
      document.body.style.overflow = "hidden";
    }
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (destroyModal && !destroyModal.hidden) {
      closeModal(destroyModal);
      openBtn.focus();
    } else if (emptyModal && !emptyModal.hidden) {
      closeModal(emptyModal);
      openBtn.focus();
    }
  });
})();
