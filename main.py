"""
main.py - Coletor central do UNABOARD

Este arquivo é a fonte principal dos dados do dashboard.

O streamlit_app.py chama registrar_uma_vez() a cada rerun/refresh.
Essa função coleta os dados, grava no historico/historico.json e retorna
o mesmo snapshot para o Streamlit renderizar Monitor, Rede e Processos.

Também é possível rodar manualmente:
    py main.py
"""

from __future__ import annotations

import json
import math
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

try:
    from dados.cpu import get_cpu
except Exception:
    get_cpu = None

try:
    from dados.disco import get_disco
except Exception:
    get_disco = None

try:
    from dados.memoria import get_memoria
except Exception:
    get_memoria = None

try:
    from dados.rede import get_rede
except Exception:
    get_rede = None

try:
    from dados.rede_qualidade import get_ping, get_packet_loss, get_jitter
except Exception:
    get_ping = get_packet_loss = get_jitter = None

try:
    from dados.gpu import get_gpu
except Exception:
    get_gpu = None

try:
    from dados.processos import get_processos
except Exception:
    get_processos = None


BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "historico" / "historico.json"
MAX_HISTORY = 80
INTERVALO_SEGUNDOS = 5


def safe_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if value is None or value == "N/A" or value == "--" or value == "":
            return default

        if isinstance(value, str):
            value = (
                value.replace("GB", "")
                .replace("MB", "")
                .replace("Mbps", "")
                .replace("ms", "")
                .replace("%", "")
                .replace(",", ".")
                .strip()
            )

        number = float(value)

        if math.isnan(number):
            return default

        return number
    except Exception:
        return default


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def read_history(
    history_file: Path | str = HISTORY_FILE,
    max_history: int = MAX_HISTORY,
) -> List[Dict[str, Any]]:
    path = Path(history_file)

    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(raw, dict):
        for key in (
            "historico",
            "history",
            "dados",
            "registros",
            "snapshots",
            "monitoramentos",
        ):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            raw = [raw]

    if not isinstance(raw, list):
        return []

    return [item for item in raw if isinstance(item, dict)][-max_history:]


def save_history(
    history: List[Dict[str, Any]],
    history_file: Path | str = HISTORY_FILE,
    max_history: int = MAX_HISTORY,
) -> None:
    path = Path(history_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = [json_safe(item) for item in history[-max_history:]]

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)

    debug_file = path.parent / "ultimo_refresh.txt"
    last_timestamp = payload[-1].get("timestamp") if payload else None
    debug_file.write_text(
        "Último refresh registrado pelo main.py\n"
        f"timestamp: {last_timestamp}\n"
        f"arquivo: {path}\n"
        f"itens_no_historico: {len(payload)}\n",
        encoding="utf-8",
    )


def get_cpu_name() -> str:
    if platform.system().lower() != "windows":
        name = platform.processor()
        return name or "CPU"

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "Get-CimInstance Win32_Processor | "
                    "Select-Object -First 1 -ExpandProperty Name"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )

        name = result.stdout.strip()
        return name or "CPU"

    except Exception:
        return "CPU"


def get_memory_data() -> Dict[str, float]:
    if get_memoria:
        try:
            data = get_memoria()
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    mem = psutil.virtual_memory()
    return {
        "total": round(mem.total / (1024**3), 2),
        "used": round(mem.used / (1024**3), 2),
        "percent": mem.percent,
    }


def get_cpu_data() -> float:
    if get_cpu:
        try:
            return float(get_cpu())
        except Exception:
            pass

    return float(psutil.cpu_percent(interval=0.2))


def get_disk_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    try:
        partitions = psutil.disk_partitions(all=False)

        for index, part in enumerate(partitions):
            if "cdrom" in part.opts.lower():
                continue

            try:
                usage = psutil.disk_usage(part.mountpoint)
            except Exception:
                continue

            label = "SSD" if index == 0 else "DISCO RÍGIDO"

            rows.append(
                {
                    "nome": label,
                    "mount": part.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "percent": usage.percent,
                }
            )

    except Exception:
        pass

    if not rows and get_disco:
        try:
            disco = get_disco()
            if isinstance(disco, dict):
                rows.append(
                    {
                        "nome": "DISCO",
                        "mount": "/",
                        "total_gb": disco.get("total", 0),
                        "used_gb": disco.get("used", 0),
                        "percent": disco.get("percent", 0),
                    }
                )
        except Exception:
            pass

    return rows


def get_network_data() -> Dict[str, Any]:
    rede: Dict[str, Any] = {"download_mbps": 0.0, "upload_mbps": 0.0}

    if get_rede:
        try:
            data = get_rede()
            if isinstance(data, dict):
                rede.update(data)
        except Exception:
            pass

    ping = loss = jitter = None

    if get_ping:
        try:
            ping = get_ping()
        except Exception:
            pass

    if get_packet_loss:
        try:
            loss = get_packet_loss()
        except Exception:
            pass

    if get_jitter:
        try:
            jitter = get_jitter()
        except Exception:
            pass

    rede.update({"ping": ping, "packet_loss": loss, "jitter": jitter})
    return rede


def get_gpu_data() -> Dict[str, Any]:
    fallback = {
        "nome": "GPU não detectada",
        "uso_gpu": 0,
        "uso_memoria_gpu": 0,
        "temperatura": None,
        "memoria_total_gb": 0,
        "memoria_usada_gb": 0,
        "memoria_livre_gb": 0,
        "memoria_compartilhada_gb": "N/A",
        "memoria_compartilhada_total_gb": "N/A",
        "memoria_dedicada_gb": "N/A",
        "memoria_dedicada_total_gb": "N/A",
        "usa_memoria_compartilhada": False,
        "clock_gpu": None,
        "clock_memoria": None,
        "driver": "--",
        "backend": "--",
        "engines": {},
    }

    if get_gpu:
        try:
            data = get_gpu()
            if isinstance(data, dict):
                fallback.update(data)
        except Exception:
            pass

    return fallback


def get_process_data() -> List[Dict[str, Any]]:
    if get_processos:
        try:
            data = get_processos()
            if isinstance(data, list):
                return data
        except Exception:
            pass

    processos: List[Dict[str, Any]] = []

    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(interval=None)
        except Exception:
            pass

    try:
        psutil.cpu_percent(interval=0.1)
    except Exception:
        pass

    for proc in psutil.process_iter(["pid", "name", "memory_info", "num_threads"]):
        try:
            processos.append(
                {
                    "pid": proc.info["pid"],
                    "nome": proc.info["name"] or "--",
                    "cpu": proc.cpu_percent(interval=None),
                    "memoria_mb": round(
                        proc.info["memory_info"].rss / (1024 * 1024),
                        2,
                    ),
                    "threads": proc.info["num_threads"],
                }
            )
        except Exception:
            continue

    processos.sort(
        key=lambda item: (
            safe_float(item.get("cpu"), 0) or 0,
            item.get("memoria_mb", 0),
        ),
        reverse=True,
    )

    return processos[:10]


def collect_snapshot_current() -> Dict[str, Any]:
    memoria = get_memory_data()
    discos = get_disk_rows()
    rede = get_network_data()
    gpu = get_gpu_data()
    cpu = get_cpu_data()
    processos = get_process_data()
    cpu_name = get_cpu_name()

    return {
        "timestamp": datetime.now(),
        "registered_by": "main.py",
        "cpu_percent": cpu,
        "cpu_name": cpu_name,
        "ram_percent": memoria.get("percent", 0),
        "ram_used_gb": memoria.get("used", 0),
        "ram_total_gb": memoria.get("total", 0),
        "download_mbps": rede.get("download_mbps", 0),
        "upload_mbps": rede.get("upload_mbps", 0),
        "ping": rede.get("ping"),
        "packet_loss": rede.get("packet_loss"),
        "jitter": rede.get("jitter"),
        "gpu_percent": gpu.get("uso_gpu", 0),
        "gpu_memory_percent": gpu.get("uso_memoria_gpu", 0),
        "gpu_temp": gpu.get("temperatura"),
        "vram_used_gb": gpu.get("memoria_usada_gb", 0),
        "vram_total_gb": gpu.get("memoria_total_gb", 0),
        "vram_free_gb": gpu.get("memoria_livre_gb", 0),
        "gpu_clock": gpu.get("clock_gpu"),
        "gpu_memory_clock": gpu.get("clock_memoria"),
        "gpu_name": gpu.get("nome", "GPU"),
        "gpu_driver": gpu.get("driver", "--"),
        "memory": memoria,
        "disks": discos,
        "network": rede,
        "gpu": gpu,
        "processes": processos,
    }


def registrar_uma_vez(
    history_file: Path | str = HISTORY_FILE,
    max_history: int = MAX_HISTORY,
) -> Dict[str, Any]:
    """
    Coleta um snapshot, salva no histórico e retorna o mesmo snapshot.

    Essa é a função que o streamlit_app.py deve chamar.
    """
    history = read_history(history_file=history_file, max_history=max_history)
    snapshot = collect_snapshot_current()

    history.append(snapshot)
    save_history(history, history_file=history_file, max_history=max_history)

    return snapshot


def main() -> None:
    print("Coletor UNABOARD iniciado. Pressione Ctrl+C para parar.")

    while True:
        snapshot = registrar_uma_vez()
        print(f"Registrado pelo main.py: {snapshot['timestamp']}")
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()
