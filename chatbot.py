from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types

from dados.cpu import get_cpu
from dados.memoria import get_memoria
from dados.gpu import get_gpu
from dados.rede import get_rede
from dados.disco import get_disco
from dados.processos import get_processos

try:
    from dados.rede_qualidade import get_ping, get_packet_loss, get_jitter
except ImportError:
    get_ping = get_packet_loss = get_jitter = None


# Para projeto local/faculdade:
# Cole sua chave aqui, se não quiser usar variável de ambiente.
API_KEY = "COLE_SUA_API_KEY_AQUI"

INSTRUCAO_SISTEMA = """
Você é o UNABOARD, um Assistente de TI avançado integrado a um painel
de monitoramento.

Sempre que o usuário fizer uma pergunta, você receberá um bloco
[DADOS DO SISTEMA NESTE MOMENTO].

Use essas informações ativas da máquina para diagnosticar problemas.
Seja direto, analítico, técnico e responda em português brasileiro,
porém de forma fácil de entender.

Tente apresentar possíveis causas, validações e soluções.

Formato da resposta:
- Não use Markdown com asteriscos, como **texto**.
- Use frases curtas.
- Separe em blocos pequenos.
- Use no máximo 4 tópicos principais.
- Quando citar valores, explique o impacto de forma objetiva.
"""


def _get_api_key() -> str:
    api_key = (
        API_KEY
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key or api_key == "COLE_SUA_API_KEY_AQUI":
        raise RuntimeError(
            "Chave da Gemini não configurada. "
            "Cole a chave em API_KEY no chatbot.py ou defina GEMINI_API_KEY."
        )

    return api_key


def _safe_get(data: Any, key: str, default: Any = "N/A") -> Any:
    if isinstance(data, dict):
        return data.get(key, default)

    return default


def gerar_relatorio_hardware_atual() -> str:
    try:
        cpu_uso = get_cpu()
        mem = get_memoria()
        gpu = get_gpu()
        rede = get_rede()
        disco = get_disco()
        processos = get_processos()

        ping = get_ping() if get_ping else "N/A"
        loss = get_packet_loss() if get_packet_loss else "N/A"
        jitter = get_jitter() if get_jitter else "N/A"

        lista_processos = ""

        if isinstance(processos, list):
            for p in processos[:5]:
                lista_processos += (
                    f"  - {_safe_get(p, 'nome')} "
                    f"(PID: {_safe_get(p, 'pid')}) | "
                    f"CPU: {_safe_get(p, 'cpu', 0)}% | "
                    f"RAM: {_safe_get(p, 'memoria_mb', 0)} MB\n"
                )

        if not lista_processos:
            lista_processos = "  - N/A\n"

        relatorio = f"""
[DADOS DO SISTEMA NESTE MOMENTO]

[HARDWARE GERAL]
- CPU: {cpu_uso}%
- RAM: {_safe_get(mem, 'used')} GB / {_safe_get(mem, 'total')} GB ({_safe_get(mem, 'percent')}%)
- Disco (/): {_safe_get(disco, 'used')} GB / {_safe_get(disco, 'total')} GB ({_safe_get(disco, 'percent')}%)
- GPU: {_safe_get(gpu, 'nome')}
- Uso GPU: {_safe_get(gpu, 'uso_gpu', 0)}%
- VRAM/Memória Usada: {_safe_get(gpu, 'memoria_usada_gb', 0)} GB
- Memória Compartilhada GPU: {_safe_get(gpu, 'memoria_compartilhada_gb', 'N/A')} GB
- Memória Dedicada GPU: {_safe_get(gpu, 'memoria_dedicada_gb', 'N/A')} GB
- Temp GPU: {_safe_get(gpu, 'temperatura')}°C

[REDE E QUALIDADE]
- Download: {_safe_get(rede, 'download_mbps', 0)} Mbps
- Upload: {_safe_get(rede, 'upload_mbps', 0)} Mbps
- Ping: {ping} ms
- Packet Loss: {loss}%
- Jitter: {jitter} ms

[TOP 5 PROCESSOS CONSUMINDO RECURSOS]
{lista_processos}
"""
        return relatorio

    except Exception as exc:
        return (
            "[AVISO: Falha ao coletar dados do hardware no momento: "
            f"{exc}]"
        )


def enviar_mensagem_com_hardware(mensagem_usuario: str) -> str:
    hardware_atual = gerar_relatorio_hardware_atual()

    prompt_injetado = (
        f"{hardware_atual}\n\n"
        f"Pergunta do usuário: {mensagem_usuario}"
    )

    # Cria um client novo por mensagem.
    # Isso evita: "Cannot send a request, as the client has been closed."
    client = genai.Client(api_key=_get_api_key())

    resposta = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt_injetado,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCAO_SISTEMA,
            temperature=0.2,
        ),
    )

    return resposta.text or "A IA não retornou uma resposta em texto."
