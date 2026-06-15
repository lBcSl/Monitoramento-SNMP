/* =========================================================
   UNABOARD - app.js
   Inicialização geral do dashboard.
   ========================================================= */

(function () {
    const U = window.UNABOARD = window.UNABOARD || {};

    U.init = function init() {
        if (typeof U.initResponsive === "function") {
            U.initResponsive();
        }

        if (typeof U.initMonitorCarousel === "function") {
            U.initMonitorCarousel();
        }

        if (typeof U.initChatbot === "function") {
            U.initChatbot();
        }
    };

    window.addEventListener("load", U.init);

    U.init();
    setTimeout(U.init, 25);
    setTimeout(U.init, 150);
    setTimeout(U.init, 500);
    setTimeout(U.init, 1000);

    if (typeof U.scheduleResize === "function") {
        setTimeout(function () { U.scheduleResize(1400); }, 1400);
        setTimeout(function () { U.scheduleResize(1800); }, 1800);
    }
})();
