(function () {
    let resizeTimer = null;

    let resizeAnimationTimer = null;

    function markResizing() {
        document.documentElement.classList.add("is-resizing");
        document.body.classList.add("is-resizing");

        if (resizeAnimationTimer) {
            clearTimeout(resizeAnimationTimer);
        }

        resizeAnimationTimer = setTimeout(function () {
            document.documentElement.classList.remove("is-resizing");
            document.body.classList.remove("is-resizing");
        }, 180);
    }


    function getParentViewportHeight() {
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
    }

    function resizeIframe() {
        try {
            markResizing();
            const frame = window.frameElement;
            if (!frame) return;

            const viewportHeight = getParentViewportHeight();
            const rect = frame.getBoundingClientRect();
            const bottomGap = 8;

            const visibleHeight = Math.max(
                620,
                Math.floor(viewportHeight - rect.top - bottomGap)
            );

            const isStackedLayout = window.matchMedia("(max-width: 1366px)").matches;
            const wrap = document.querySelector(".dashboard-wrap");

            /*
             * Importante:
             * No layout empilhado NÃO usamos document.body.scrollHeight nem
             * document.documentElement.scrollHeight, porque eles podem passar a
             * refletir a própria altura do iframe. Isso criava um loop:
             * iframe maior -> scrollHeight maior -> iframe ainda maior.
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
    }

    function scheduleResize(delay = 0) {
        if (resizeTimer) {
            clearTimeout(resizeTimer);
        }

        if (delay <= 40) {
            window.requestAnimationFrame(resizeIframe);
            return;
        }

        resizeTimer = setTimeout(function () {
            window.requestAnimationFrame(resizeIframe);
        }, delay);
    }

    function initMonitorCarousel() {
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

        function setPage(page) {
            currentPage = page;

            const pages = card.querySelectorAll(".monitor-page");
            pages.forEach((el) => {
                if (el.dataset.page === page) {
                    el.classList.add("is-active");
                } else {
                    el.classList.remove("is-active");
                }
            });

            pagesTrack.style.transform = page === "rede"
                ? "translateX(-50%)"
                : "translateX(0)";

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

            scheduleResize(80);
            scheduleResize(380);
        }

        btn.addEventListener("click", function () {
            setPage(currentPage === "monitor" ? "rede" : "monitor");
        });

        setPage("monitor");
    }

    function initChatbot() {
        const STORAGE_KEY = "unaboard_chat_messages_v1";

        const messagesEl = document.getElementById("chat-messages");
        const inputEl = document.getElementById("chat-input");
        const sendBtn = document.getElementById("chat-send");

        if (!messagesEl || !inputEl || !sendBtn) return;

        if (messagesEl.dataset.chatReady === "1") return;
        messagesEl.dataset.chatReady = "1";

        function escapeHtml(text) {
            return String(text)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#039;");
        }

        function defaultMessages() {
            return [
                {
                    role: "bot",
                    content: "Olá! Posso ajudar a interpretar os dados do monitoramento."
                }
            ];
        }

        function loadMessages() {
            try {
                const saved = sessionStorage.getItem(STORAGE_KEY);
                if (!saved) return null;

                const parsed = JSON.parse(saved);
                return Array.isArray(parsed) ? parsed : null;
            } catch (error) {
                return null;
            }
        }

        function saveMessages(messages) {
            try {
                sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-30)));
            } catch (error) {}
        }

        let messages = loadMessages() || defaultMessages();

        function renderMessages() {
            messagesEl.innerHTML = "";

            for (const msg of messages) {
                const bubble = document.createElement("div");
                bubble.className = "chat-bubble " + (msg.role === "user" ? "user" : "bot");
                bubble.innerHTML = escapeHtml(msg.content);
                messagesEl.appendChild(bubble);
            }

            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function addMessage(role, content) {
            messages.push({ role, content });
            saveMessages(messages);
            renderMessages();
        }

        // PONTO DE INTEGRAÇÃO FUTURA:
        // Troque esta função por fetch/API/IA quando o backend estiver pronto.
        async function generateBotResponse(message) {
            const text = message.toLowerCase().trim();

            if (text.includes("cpu")) {
                return "Posso analisar uso de CPU, picos e possíveis gargalos. Em uma integração futura, vou cruzar sua pergunta com o historico.json.";
            }

            if (text.includes("gpu") || text.includes("vram") || text.includes("memória gpu") || text.includes("memoria gpu")) {
                return "Posso analisar uso de GPU, memória dedicada/compartilhada e possíveis gargalos gráficos.";
            }

            if (text.includes("ram") || text.includes("memória") || text.includes("memoria")) {
                return "Posso analisar consumo de RAM, processos mais pesados e tendência no histórico.";
            }

            if (text.includes("rede") || text.includes("ping") || text.includes("jitter") || text.includes("download") || text.includes("upload")) {
                return "Posso interpretar ping, jitter, perda de pacotes, download e upload com base nos gráficos.";
            }

            if (text.includes("limpar") || text.includes("resetar chat")) {
                messages = defaultMessages();
                saveMessages(messages);
                renderMessages();
                return "Conversa limpa.";
            }

            return "Mensagem recebida. A aba já está funcional; falta apenas conectar uma IA/API para responder com análise real dos dados.";
        }

        async function handleSend() {
            const value = inputEl.value.trim();
            if (!value) return;

            inputEl.value = "";
            addMessage("user", value);

            sendBtn.disabled = true;
            inputEl.disabled = true;

            try {
                const answer = await generateBotResponse(value);
                addMessage("bot", answer);
            } catch (error) {
                addMessage("bot", "Não consegui gerar uma resposta agora.");
            } finally {
                sendBtn.disabled = false;
                inputEl.disabled = false;
                inputEl.focus();
            }
        }

        sendBtn.addEventListener("click", handleSend);

        inputEl.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                handleSend();
            }
        });

        renderMessages();
    }

    function init() {
        resizeIframe();
        initMonitorCarousel();
        initChatbot();

        if (!window.__unaboardResizeObserverReady) {
            window.__unaboardResizeObserverReady = true;

            try {
                const observer = new ResizeObserver(function () {
                    scheduleResize(160);
                });

                const wrap = document.querySelector(".dashboard-wrap");
                if (wrap) observer.observe(wrap);
            } catch (error) {}

            try {
                const mutationObserver = new MutationObserver(function () {
                    scheduleResize(120);
                });

                mutationObserver.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true
                });
            } catch (error) {}
        }

        // Plotly e o layout responsivo podem terminar de ajustar depois do load.
        setTimeout(resizeIframe, 250);
        setTimeout(resizeIframe, 750);
        setTimeout(resizeIframe, 1500);
    }

    window.addEventListener("load", init);
    window.addEventListener("resize", function () { scheduleResize(0); });

    try {
        window.parent.addEventListener("resize", function () { scheduleResize(0); });
    } catch (error) {}

    try {
        if (window.parent && window.parent.visualViewport) {
            window.parent.visualViewport.addEventListener("resize", function () { scheduleResize(0); });
            window.parent.visualViewport.addEventListener("scroll", function () { scheduleResize(0); });
        }
    } catch (error) {}

    init();
    setTimeout(init, 25);
    setTimeout(init, 150);
    setTimeout(init, 500);
    setTimeout(init, 1000);
    setTimeout(function () { scheduleResize(1400); }, 1400);
    setTimeout(function () { scheduleResize(1800); }, 1800);
})();
