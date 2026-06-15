/* =========================================================
   UNABOARD - animacao.js
   Controle de animações/transições durante resize.
   ========================================================= */

(function () {
    const U = window.UNABOARD = window.UNABOARD || {};
    U.state = U.state || {};

    U.markResizing = function markResizing() {
        document.documentElement.classList.add("is-resizing");
        document.body.classList.add("is-resizing");

        if (U.state.resizeAnimationTimer) {
            clearTimeout(U.state.resizeAnimationTimer);
        }

        U.state.resizeAnimationTimer = setTimeout(function () {
            document.documentElement.classList.remove("is-resizing");
            document.body.classList.remove("is-resizing");
        }, 180);
    };
})();
