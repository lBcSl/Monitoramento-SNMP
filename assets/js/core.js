/* =========================================================
   UNABOARD - core.js
   Funções base e namespace global do dashboard.
   ========================================================= */

(function () {
    window.UNABOARD = window.UNABOARD || {};

    const U = window.UNABOARD;

    U.state = U.state || {
        resizeTimer: null,
        resizeAnimationTimer: null,
        observersReady: false
    };

    U.escapeHtml = function escapeHtml(text) {
        return String(text)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    };
})();
