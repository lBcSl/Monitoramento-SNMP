from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot import enviar_mensagem_com_hardware


app = FastAPI(title="UNABOARD Chatbot API")

app.add_middleware(
    CORSMiddleware,
    # components.html usa iframe e pode enviar Origin: null.
    # Para projeto local/faculdade, liberar geral evita bloqueio de CORS.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/chat")
def chat_info() -> dict[str, str]:
    return {
        "status": "online",
        "message": "Use POST /chat para enviar mensagens. Para testar no navegador, acesse /docs ou /health.",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    message = payload.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Mensagem vazia.",
        )

    try:
        answer = enviar_mensagem_com_hardware(message)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao consultar o chatbot: {exc}",
        ) from exc

    return ChatResponse(answer=answer)
