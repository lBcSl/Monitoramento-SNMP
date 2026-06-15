/* =========================================================
   UNABOARD - chatbot.js
   Chat local integrado à API FastAPI em 127.0.0.1:8765.
   ========================================================= */

(function () {
    const U = window.UNABOARD = window.UNABOARD || {};

    U.initChatbot = function initChatbot() {
        const STORAGE_KEY = "unaboard_chat_messages_api_v1";
        const API_URL = "http://127.0.0.1:8765/chat";

        const messagesEl = document.getElementById("chat-messages");
        const inputEl = document.getElementById("chat-input");
        const sendBtn = document.getElementById("chat-send");

        if (!messagesEl || !inputEl || !sendBtn) return;

        if (messagesEl.dataset.chatReady === "1") return;
        messagesEl.dataset.chatReady = "1";

        function formatBotText(text) {
            let safe = U.escapeHtml(text || "");

            safe = safe
                .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                .replace(/\*(.*?)\*/g, "<em>$1</em>");

            safe = safe.replace(/\r\n/g, "\n");

            // Transforma listas simples em linhas visuais mais agradáveis.
            safe = safe.replace(/\n\s*[-•]\s+/g, "\n• ");

            // Mantém quebras de linha da resposta.
            safe = safe.replace(/\n/g, "<br>");

            return safe;
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
                bubble.innerHTML = msg.role === "bot"
                    ? formatBotText(msg.content)
                    : U.escapeHtml(msg.content);

                messagesEl.appendChild(bubble);
            }

            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function addMessage(role, content) {
            messages.push({ role, content });
            saveMessages(messages);
            renderMessages();

            if (typeof U.scheduleResize === "function") {
                U.scheduleResize(120);
            }
        }

        async function askLocalApi(message) {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                let detail = "Erro ao consultar API local.";

                try {
                    const errorData = await response.json();
                    detail = errorData.detail || errorData.error || detail;
                } catch (error) {}

                throw new Error(detail);
            }

            const data = await response.json();
            return data.answer || "A API respondeu, mas não retornou texto.";
        }

        async function handleSend() {
            const value = inputEl.value.trim();
            if (!value) return;

            inputEl.value = "";
            addMessage("user", value);

            sendBtn.disabled = true;
            inputEl.disabled = true;
            sendBtn.title = "Enviando...";

            try {
                const answer = await askLocalApi(value);
                addMessage("bot", answer);
            } catch (error) {
                addMessage(
                    "bot",
                    "Não consegui consultar a API local. " +
                    "Detalhe: " + (error && error.message ? error.message : String(error)) +
                    "\n\nVerifique se a API está rodando com: py -m uvicorn chatbot_api:app --host 127.0.0.1 --port 8765"
                );
            } finally {
                sendBtn.disabled = false;
                inputEl.disabled = false;
                sendBtn.title = "Enviar";
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
    };
})();
