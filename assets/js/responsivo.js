/* =========================================================
   UNABOARD - responsivo.js
   Ajuste de altura do iframe e comportamento responsivo.
   ========================================================= */

(function () {
    const U = window.UNABOARD = window.UNABOARD || {};
    U.state = U.state || {};

    U.getParentViewportHeight = function getParentViewportHeight() {
        try {
            if (window.parent && window.parent.visualViewport) {
                return window.parent.visualViewport.height;
            }
        } catch (error) {}

        try {
            return window.parent.innerHeight || window.innerHeight || 900;
        } catch (error) {
            return window.innerHeight || 900;
        }
    };

    U.resizeIframe = function resizeIframe() {
        try {
            if (typeof U.markResizing === "function") {
                U.markResizing();
            }

            const frame = window.frameElement;
            if (!frame) return;

            const viewportHeight = U.getParentViewportHeight();
            const rect = frame.getBoundingClientRect();
            const bottomGap = 8;

            const visibleHeight = Math.max(
                620,
                Math.floor(viewportHeight - rect.top - bottomGap)
            );

            const isStackedLayout = window.matchMedia("(max-width: 1366px)").matches;
            const wrap = document.querySelector(".dashboard-wrap");

            /*
             * No layout empilhado NÃO usamos document.body.scrollHeight nem
             * document.documentElement.scrollHeight, porque eles podem passar a
             * refletir a própria altura do iframe e criar loop de crescimento.
             */
            if (isStackedLayout) {
                document.documentElement.style.height = "auto";
                document.body.style.height = "auto";
                document.documentElement.style.minHeight = "0";
                document.body.style.minHeight = "0";
                document.documentElement.style.overflowX = "hidden";
                document.body.style.overflowX = "hidden";
                document.documentElement.style.overflowY = "hidden";
                document.body.style.overflowY = "hidden";

                let contentHeight = visibleHeight;

                if (wrap) {
                    const wrapRect = wrap.getBoundingClientRect();

                    contentHeight = Math.ceil(Math.max(
                        wrap.offsetHeight || 0,
                        wrap.scrollHeight || 0,
                        wrapRect.height || 0
                    ));
                }

                const finalHeight = Math.max(visibleHeight, contentHeight + 2);

                frame.style.height = finalHeight + "px";
                frame.style.minHeight = finalHeight + "px";
                frame.setAttribute("height", String(finalHeight));
            } else {
                const finalHeight = visibleHeight;

                frame.style.height = finalHeight + "px";
                frame.style.minHeight = finalHeight + "px";
                frame.setAttribute("height", String(finalHeight));

                document.documentElement.style.height = finalHeight + "px";
                document.body.style.height = finalHeight + "px";
                document.documentElement.style.minHeight = "0";
                document.body.style.minHeight = "0";
                document.documentElement.style.overflow = "hidden";
                document.body.style.overflow = "hidden";
            }
        } catch (error) {}
    };

    U.scheduleResize = function scheduleResize(delay = 0) {
        if (U.state.resizeTimer) {
            clearTimeout(U.state.resizeTimer);
        }

        if (delay <= 40) {
            window.requestAnimationFrame(U.resizeIframe);
            return;
        }

        U.state.resizeTimer = setTimeout(function () {
            window.requestAnimationFrame(U.resizeIframe);
        }, delay);
    };

    U.initResponsive = function initResponsive() {
        if (typeof U.resizeIframe === "function") {
            U.resizeIframe();
        }

        if (!U.state.observersReady) {
            U.state.observersReady = true;

            try {
                const observer = new ResizeObserver(function () {
                    U.scheduleResize(160);
                });

                const wrap = document.querySelector(".dashboard-wrap");
                if (wrap) observer.observe(wrap);
            } catch (error) {}

            try {
                const mutationObserver = new MutationObserver(function () {
                    U.scheduleResize(120);
                });

                mutationObserver.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true
                });
            } catch (error) {}
        }

        // Plotly e o layout responsivo podem terminar de ajustar depois do load.
        setTimeout(U.resizeIframe, 250);
        setTimeout(U.resizeIframe, 750);
        setTimeout(U.resizeIframe, 1500);
    };

    window.addEventListener("resize", function () {
        U.scheduleResize(0);
    });

    try {
        window.parent.addEventListener("resize", function () {
            U.scheduleResize(0);
        });
    } catch (error) {}

    try {
        if (window.parent && window.parent.visualViewport) {
            window.parent.visualViewport.addEventListener("resize", function () {
                U.scheduleResize(0);
            });

            window.parent.visualViewport.addEventListener("scroll", function () {
                U.scheduleResize(0);
            });
        }
    } catch (error) {}
})();
