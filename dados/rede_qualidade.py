"""
dados/rede_qualidade.py

Versão com timeout para não travar o main.py/Streamlit.

Funções compatíveis:
- get_ping()
- get_packet_loss()
- get_jitter()
- get_rede_qualidade()

Observação:
As três funções usam um cache curto. Então, se o main.py chamar:
    get_ping()
    get_packet_loss()
    get_jitter()
em sequência, o código executa apenas 1 teste de ping e reaproveita o resultado.
"""

import os
import re
import time
import platform
import subprocess


_DEFAULT_HOST = "1.1.1.1"
_DEFAULT_COUNT = 4
_TIMEOUT_POR_PACOTE_MS = 1000
_CACHE_SECONDS = 5

_LAST_RESULT = {
    "host": None,
    "timestamp": 0,
    "data": None,
}


def _run_ping(host=_DEFAULT_HOST, count=_DEFAULT_COUNT):
    """
    Executa ping com timeout.
    No Windows:
        ping -n 4 -w 1000 1.1.1.1
    No Linux/macOS:
        ping -c 4 -W 1 1.1.1.1
    """
    system = platform.system().lower()

    if "windows" in system:
        cmd = [
            "ping",
            "-n", str(count),
            "-w", str(_TIMEOUT_POR_PACOTE_MS),
            host,
        ]
        timeout_total = count * (_TIMEOUT_POR_PACOTE_MS / 1000) + 3
    else:
        cmd = [
            "ping",
            "-c", str(count),
            "-W", str(max(1, int(_TIMEOUT_POR_PACOTE_MS / 1000))),
            host,
        ]
        timeout_total = count * max(1, int(_TIMEOUT_POR_PACOTE_MS / 1000)) + 3

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_total,
            creationflags=creationflags,
        )

        return (result.stdout or "") + "\n" + (result.stderr or "")

    except subprocess.TimeoutExpired:
        return ""

    except Exception:
        return ""


def _parse_ping_output(output):
    """
    Retorna:
    {
        "ping": float ou "N/A",
        "packet_loss": float ou "N/A",
        "jitter": float ou "N/A",
        "times": [...]
    }
    """
    if not output:
        return {
            "ping": "N/A",
            "packet_loss": "N/A",
            "jitter": "N/A",
            "times": [],
        }

    normalized = output.replace(",", ".")

    # Exemplos:
    # Windows PT-BR: tempo=3ms / tempo<1ms
    # Windows EN: time=3ms / time<1ms
    # Linux: time=3.21 ms
    times = []

    for match in re.finditer(r"(?:tempo|time)\s*[=<]\s*(\d+(?:\.\d+)?)\s*ms", normalized, re.IGNORECASE):
        try:
            value = float(match.group(1))
            # Quando o Windows mostra <1ms, o regex pega 1.
            # Para não superestimar, podemos tratar como 0.5.
            full = match.group(0)
            if "<" in full:
                value = 0.5
            times.append(value)
        except Exception:
            pass

    # Packet loss:
    # PT-BR: (0% de perda)
    # EN: (0% loss)
    packet_loss = "N/A"

    loss_patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*de perda",
        r"(\d+(?:\.\d+)?)\s*%\s*loss",
        r"\((\d+(?:\.\d+)?)\s*%",
    ]

    for pattern in loss_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            try:
                packet_loss = float(match.group(1))
                break
            except Exception:
                pass

    # Ping médio:
    # Preferência 1: média/average do próprio comando.
    ping = "N/A"

    avg_patterns = [
        r"(?:m[eé]dia|average)\s*=\s*(\d+(?:\.\d+)?)\s*ms",
        r"(?:avg|mdev)\s*=\s*[\d\.]+/(\d+(?:\.\d+)?)/",
    ]

    for pattern in avg_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            try:
                ping = round(float(match.group(1)), 2)
                break
            except Exception:
                pass

    # Preferência 2: calcula pela lista de tempos.
    if ping == "N/A" and times:
        ping = round(sum(times) / len(times), 2)

    # Jitter simples:
    # média da diferença absoluta entre pings consecutivos.
    if len(times) >= 2:
        diffs = [abs(times[i] - times[i - 1]) for i in range(1, len(times))]
        jitter = round(sum(diffs) / len(diffs), 2)
    elif len(times) == 1:
        jitter = 0.0
    else:
        jitter = "N/A"

    return {
        "ping": ping,
        "packet_loss": packet_loss,
        "jitter": jitter,
        "times": times,
    }


def get_rede_qualidade(host=_DEFAULT_HOST, count=_DEFAULT_COUNT):
    """
    Executa um teste único e retorna ping, packet loss e jitter.
    """
    now = time.time()

    if (
        _LAST_RESULT["data"] is not None
        and _LAST_RESULT["host"] == host
        and now - _LAST_RESULT["timestamp"] <= _CACHE_SECONDS
    ):
        return _LAST_RESULT["data"]

    output = _run_ping(host=host, count=count)
    data = _parse_ping_output(output)

    _LAST_RESULT["host"] = host
    _LAST_RESULT["timestamp"] = now
    _LAST_RESULT["data"] = data

    return data


def get_ping(host=_DEFAULT_HOST):
    return get_rede_qualidade(host=host)["ping"]


def get_packet_loss(host=_DEFAULT_HOST):
    return get_rede_qualidade(host=host)["packet_loss"]


def get_jitter(host=_DEFAULT_HOST):
    return get_rede_qualidade(host=host)["jitter"]


if __name__ == "__main__":
    dados = get_rede_qualidade()
    print(f"Ping: {dados['ping']} ms")
    print(f"Packet Loss: {dados['packet_loss']}%")
    print(f"Jitter: {dados['jitter']} ms")
    print(f"Tempos: {dados['times']}"
