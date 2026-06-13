(function () {
    function getParentViewportHeight() {
        try {
            if (window.parent && window.parent.visualViewport) {
                return window.parent.visualViewport.height;
            }
        } catch (error) {}

        try {
            return window.parent.innerHeight || 900;
        } catch (error) {
            return 900;
        }
    }

    function resizeIframe() {
        try {
            const frame = window.frameElement;
            if (!frame) return;

            const viewportHeight = getParentViewportHeight();
            const rect = frame.getBoundingClientRect();
            const bottomGap = 8;
            const availableHeight = Math.max(600, viewportHeight - rect.top - bottomGap);

            frame.style.height = availableHeight + "px";
            frame.style.minHeight = availableHeight + "px";

            document.documentElement.style.height = availableHeight + "px";
            document.body.style.height = availableHeight + "px";
            document.documentElement.style.minHeight = "0";
            document.body.style.minHeight = "0";
            document.documentElement.style.overflow = "hidden";
            document.body.style.overflow = "hidden";
        } catch (error) {}
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
    }

    window.addEventListener("load", init);
    window.addEventListener("resize", resizeIframe);

    try {
        window.parent.addEventListener("resize", resizeIframe);
    } catch (error) {}

    try {
        if (window.parent && window.parent.visualViewport) {
            window.parent.visualViewport.addEventListener("resize", resizeIframe);
            window.parent.visualViewport.addEventListener("scroll", resizeIframe);
        }
    } catch (error) {}

    init();
    setTimeout(init, 25);
    setTimeout(init, 150);
    setTimeout(init, 500);
    setTimeout(init, 1000);
})();
