/* =========================================================
   UNABOARD - monitor.js
   Alternância entre página Monitor e página Rede.
   ========================================================= */

(function () {
    const U = window.UNABOARD = window.UNABOARD || {};

    U.initMonitorCarousel = function initMonitorCarousel() {
        const card = document.getElementById("monitor-card");
        const btn = document.getElementById("monitor-page-btn");
        const titleText = document.getElementById("monitor-title-text");
        const titleIcon = document.getElementById("monitor-title-icon");
        const pagesTrack = document.getElementById("monitor-pages");

        if (!card || !btn || !titleText || !titleIcon || !pagesTrack) return;

        if (card.dataset.carouselReady === "1") return;
        card.dataset.carouselReady = "1";

        const monitorIconHtml = card.dataset.monitorIcon || "";
        const redeIconHtml = card.dataset.redeIcon || "";

        let currentPage = "monitor";

        let slideTimer = null;

        function setPage(page) {
            currentPage = page;

            pagesTrack.classList.add("is-monitor-sliding");

            if (slideTimer) {
                clearTimeout(slideTimer);
            }

            slideTimer = setTimeout(function () {
                pagesTrack.classList.remove("is-monitor-sliding");
            }, 460);

            const pages = card.querySelectorAll(".monitor-page");
            pages.forEach((el) => {
                if (el.dataset.page === page) {
                    el.classList.add("is-active");
                } else {
                    el.classList.remove("is-active");
                }
            });

            window.requestAnimationFrame(function () {
                pagesTrack.style.transform = page === "rede"
                    ? "translateX(-50%)"
                    : "translateX(0)";
            });

            if (page === "rede") {
                titleText.textContent = "REDE";
                titleIcon.innerHTML = redeIconHtml;
                btn.textContent = "‹";
                btn.title = "Voltar para Monitor";
            } else {
                titleText.textContent = "MONITOR";
                titleIcon.innerHTML = monitorIconHtml;
                btn.textContent = "›";
                btn.title = "Ir para Rede";
            }

            if (typeof U.scheduleResize === "function") {
                U.scheduleResize(80);
                U.scheduleResize(380);
            }
        }

        btn.addEventListener("click", function () {
            setPage(currentPage === "monitor" ? "rede" : "monitor");
        });

        setPage("monitor");
    };
})();
