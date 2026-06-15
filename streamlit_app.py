"""
UNABOARD - Dashboard Streamlit
Design atualizado conforme o layout enviado:
- Topbar branco
- Chatbot à esquerda
- Monitor + Processos no centro
- Gráficos grande à direita
- Sem card de Avisos

Execute:
    python -m streamlit run streamlit_app.py
"""

from __future__ import annotations

import base64
import html
import json
import math
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import psutil
import streamlit as st
import streamlit.components.v1 as components

try:
    from main import registrar_uma_vez as main_registrar_uma_vez
except Exception:
    main_registrar_uma_vez = None

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

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





APP_NAME = "UNABOARD"
USER_NAME = "VENSX"
REFRESH_MS = 0  # autorefresh desativado; use F5 para registrar novo histórico
MAX_HISTORY = 80


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
HISTORY_FILE = BASE_DIR / "historico" / "historico.json"


def load_text(relative_path: str) -> str:
    """Carrega arquivos de assets de forma segura, independente do diretório atual."""
    path = BASE_DIR / relative_path
    return path.read_text(encoding="utf-8")


def load_js_script(relative_path: str) -> str:
    """Carrega um arquivo JS externo e injeta no HTML do componente."""
    return f"<script>\n{load_text(relative_path)}\n</script>"


def load_js_scripts(relative_paths: List[str]) -> str:
    """Carrega vários arquivos JS externos em ordem e injeta no componente."""
    return "\n".join(load_js_script(path) for path in relative_paths)


def render_template(relative_path: str, **context: str) -> str:
    template = load_text(relative_path)
    for key, value in context.items():
        template = template.replace("{{" + key + "}}", value)
    return template


@st.cache_data(show_spinner=False)
def svg_to_data_uri(relative_path: str) -> str:
    path = BASE_DIR / relative_path
    if not path.exists():
        return ""

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/svg+xml;base64," + encoded


def icon_img(name: str, class_name: str = "svg-icon") -> str:
    """Retorna um <img> de SVG usando assets/icons/<name>.svg."""
    src = svg_to_data_uri(f"assets/icons/{name}.svg")
    if not src:
        return ""
    return f'<img class="{class_name}" src="{src}" alt="">'





# =========================================================
# Helpers
# =========================================================

def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


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


def fmt_num(value: Any, suffix: str = "", decimals: int = 1) -> str:
    number = safe_float(value, None)
    if number is None:
        return "--"

    if float(number).is_integer():
        text = f"{int(number)}"
    else:
        text = f"{number:.{decimals}f}".rstrip("0").rstrip(".")

    return f"{text}{suffix}"


def fmt_gb(value: Any) -> str:
    number = safe_float(value, None)
    if number is None:
        return "--"
    return f"{fmt_num(number, '', 2)}GB"


def fmt_gb_pair(used: Any, total: Any) -> str:
    used_num = safe_float(used, None)
    total_num = safe_float(total, None)

    if used_num is None and total_num is None:
        return "--"
    if total_num is None:
        return fmt_gb(used_num)
    if used_num is None:
        return f"--/{fmt_gb(total_num)}"

    return f"{fmt_gb(used_num)}/{fmt_gb(total_num)}"


def fmt_percent(value: Any) -> str:
    return f"{fmt_num(value, '', 1)}%"


def fmt_mbps(value: Any) -> str:
    return f"{fmt_num(value, '', 2)} Mbps"


def minmax_from_history(key: str) -> tuple[Optional[float], Optional[float]]:
    values = []
    for item in st.session_state.get("history", []):
        value = safe_float(item.get(key), None)
        if value is not None:
            values.append(value)

    if not values:
        return None, None

    return min(values), max(values)


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
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
            ],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        name = (result.stdout or "").strip()
        return name or "CPU"
    except Exception:
        return "CPU"



# =========================================================
# Histórico JSON
# =========================================================

def parse_datetime(value: Any):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    value = str(value).strip()

    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y, %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value[:26], fmt)
        except Exception:
            pass

    return None


def get_nested(data: Dict[str, Any], *paths, default=None):
    for path in paths:
        try:
            current = data

            if isinstance(path, tuple):
                for part in path:
                    current = current[part]
                return current

            if path in data:
                return data[path]
        except Exception:
            pass

    return default


def read_json_any(path: Path):
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8", errors="ignore").strip()

    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        # Suporte a JSON Lines, caso exista um JSON por linha.
        rows = []

        for line in text.splitlines():
            line = line.strip().rstrip(",")

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except Exception:
                pass

        return rows or None


def normalize_history_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    data = raw

    for wrapper in ("dados", "data", "snapshot", "monitoramento", "hardware"):
        if isinstance(raw.get(wrapper), dict):
            data = raw.get(wrapper)
            break

    gpu = get_nested(data, "gpu", "GPU", "placa_video", "video", default={})
    rede = get_nested(data, "rede", "REDE", "network", default={})
    qualidade = get_nested(data, "qualidade_rede", "QUALIDADE DA REDE", "rede_qualidade", "qualidade", default={})
    memoria = get_nested(data, "memoria", "MEMÓRIA", "MEMORIA", "ram", "RAM", default={})

    if not isinstance(gpu, dict):
        gpu = {}

    if not isinstance(rede, dict):
        rede = {}

    if not isinstance(qualidade, dict):
        qualidade = {}

    if not isinstance(memoria, dict):
        memoria = {}

    timestamp = (
        parse_datetime(get_nested(raw, "timestamp", "data", "data_hora", "datetime", "Data do monitoramento"))
        or parse_datetime(get_nested(data, "timestamp", "data", "data_hora", "datetime", "Data do monitoramento"))
        or datetime.now()
    )

    ram_percent = get_nested(
        data,
        "ram_percent",
        "RAM",
        "ram",
        ("memoria", "percent"),
        ("memoria", "porcentagem"),
        default=None,
    )

    if ram_percent is None:
        ram_percent = get_nested(memoria, "percent", "porcentagem", "uso", "RAM", default=None)

    ram_used_gb = get_nested(
        data,
        "ram_used_gb",
        "ram_usada",
        "RAM usada",
        ("memoria", "used"),
        ("memoria", "usada"),
        default=None,
    )

    if ram_used_gb is None:
        ram_used_gb = get_nested(memoria, "used", "usada", "RAM usada", "ram_usada", default=None)

    item = {
        "timestamp": timestamp,
        "cpu_percent": safe_float(get_nested(data, "cpu_percent", "CPU", "cpu", "uso_cpu", default=None), 0),
        "ram_percent": safe_float(ram_percent, 0),
        "ram_used_gb": safe_float(ram_used_gb, 0),

        "download_mbps": safe_float(get_nested(data, "download_mbps", "Download", "download", ("rede", "download"), default=None), 0),
        "upload_mbps": safe_float(get_nested(data, "upload_mbps", "Upload", "upload", ("rede", "upload"), default=None), 0),

        "ping": safe_float(get_nested(data, "ping", "Ping", ("qualidade_rede", "ping"), default=None), None),
        "packet_loss": safe_float(get_nested(data, "packet_loss", "Packet Loss", "packet loss", ("qualidade_rede", "packet_loss"), default=None), None),
        "jitter": safe_float(get_nested(data, "jitter", "Jitter", ("qualidade_rede", "jitter"), default=None), None),

        "gpu_percent": safe_float(get_nested(data, "gpu_percent", "Uso GPU", "uso_gpu", ("gpu", "uso_gpu"), default=None), 0),
        "gpu_memory_percent": safe_float(get_nested(data, "gpu_memory_percent", "Uso Memória GPU", "uso_memoria_gpu", ("gpu", "uso_memoria_gpu"), default=None), 0),
        "gpu_temp": safe_float(get_nested(data, "gpu_temp", "Temperatura", "temperatura", ("gpu", "temperatura"), default=None), None),
    }

    # Fallbacks por blocos.
    if item["gpu_percent"] == 0:
        item["gpu_percent"] = safe_float(get_nested(gpu, "uso_gpu", "Uso GPU", "gpu_percent", default=0), 0)

    if item["gpu_memory_percent"] == 0:
        item["gpu_memory_percent"] = safe_float(get_nested(gpu, "uso_memoria_gpu", "Uso Memória GPU", "gpu_memory_percent", default=0), 0)

    if item["gpu_temp"] is None:
        item["gpu_temp"] = safe_float(get_nested(gpu, "temperatura", "Temperatura", "gpu_temp", default=None), None)

    if item["download_mbps"] == 0:
        item["download_mbps"] = safe_float(get_nested(rede, "download_mbps", "download", "Download", default=0), 0)

    if item["upload_mbps"] == 0:
        item["upload_mbps"] = safe_float(get_nested(rede, "upload_mbps", "upload", "Upload", default=0), 0)

    if item["ping"] is None:
        item["ping"] = safe_float(get_nested(qualidade, "ping", "Ping", default=None), None)

    if item["packet_loss"] is None:
        item["packet_loss"] = safe_float(get_nested(qualidade, "packet_loss", "Packet Loss", "packet loss", default=None), None)

    if item["jitter"] is None:
        item["jitter"] = safe_float(get_nested(qualidade, "jitter", "Jitter", default=None), None)

    return item


def load_history_from_file(path: Path = HISTORY_FILE) -> List[Dict[str, Any]]:
    raw = read_json_any(path)

    if raw is None:
        return []

    if isinstance(raw, dict):
        for key in ("historico", "history", "dados", "registros", "snapshots", "monitoramentos"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            raw = [raw]

    if not isinstance(raw, list):
        return []

    normalized = []

    for item in raw:
        if isinstance(item, dict):
            row = normalize_history_item(item)

            if row:
                normalized.append(row)

    normalized.sort(key=lambda x: x.get("timestamp") or datetime.min)
    return normalized[-MAX_HISTORY:]


def json_safe(value: Any) -> Any:
    """Converte snapshots com datetime/objetos para JSON."""
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


def save_history_to_file(
    history: List[Dict[str, Any]],
    path: Path = HISTORY_FILE,
) -> None:
    """
    Salva o histórico no arquivo historico/historico.json.

    Também grava no diretório atual do terminal, se ele for diferente do
    diretório do streamlit_app.py. Isso evita confusão quando o projeto é
    executado de outra pasta e o usuário olha outro historico.json.
    """
    payload = [json_safe(item) for item in history[-MAX_HISTORY:]]

    target_paths = [path]

    cwd_history = Path.cwd() / "historico" / "historico.json"
    try:
        if cwd_history.resolve() != path.resolve():
            target_paths.append(cwd_history)
    except Exception:
        target_paths.append(cwd_history)

    last_timestamp = None
    if history:
        last_timestamp = history[-1].get("timestamp")

    for target in target_paths:
        target.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = target.with_suffix(target.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(target)

        debug_file = target.parent / "ultimo_refresh.txt"
        debug_file.write_text(
            "Último refresh registrado pelo Streamlit\n"
            f"timestamp: {last_timestamp}\n"
            f"arquivo: {target}\n"
            f"itens_no_historico: {len(payload)}\n",
            encoding="utf-8",
        )


def register_streamlit_refresh_history() -> Dict[str, Any]:
    """
    Registra um snapshot usando o main.py.

    O Streamlit não coleta mais os dados diretamente como fonte principal.
    Ele chama main.registrar_uma_vez(), que:
    - coleta CPU, RAM, GPU, rede e processos;
    - salva em historico/historico.json;
    - devolve o mesmo snapshot para os cards.

    Assim, Monitor, Rede e Processos exibem o mesmo dado que acabou de ser
    registrado pelo main.py no histórico.
    """
    if main_registrar_uma_vez is not None:
        try:
            snapshot = main_registrar_uma_vez(
                history_file=HISTORY_FILE,
                max_history=MAX_HISTORY,
            )

            # Recarrega o histórico do disco para os gráficos/min/max.
            st.session_state.history = load_history_from_file()
            st.session_state.history_loaded_from_file = True
            st.session_state.last_history_saved_at = snapshot.get("timestamp")
            st.session_state.main_py_error = ""

            return snapshot

        except Exception as exc:
            # Fallback para o painel não quebrar caso o main.py tenha algum erro.
            st.session_state.main_py_error = str(exc)

    history = load_history_from_file()
    snapshot = collect_snapshot_current()
    snapshot["registered_by"] = "streamlit_app_fallback"

    history.append(snapshot)
    history = history[-MAX_HISTORY:]

    save_history_to_file(history)

    st.session_state.history = history
    st.session_state.history_loaded_from_file = True
    st.session_state.last_history_saved_at = snapshot.get("timestamp")

    return snapshot


# =========================================================
# Coleta
# =========================================================

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
    rede = {"download_mbps": 0.0, "upload_mbps": 0.0}

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

    processos = []

    # Primeira leitura para o psutil calcular CPU dos processos.
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(interval=None)
        except Exception:
            pass

    # Pequena pausa interna para melhorar a leitura de CPU.
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
                    "memoria_mb": round(proc.info["memory_info"].rss / (1024 * 1024), 2),
                    "threads": proc.info["num_threads"],
                }
            )
        except Exception:
            continue

    processos.sort(key=lambda x: (safe_float(x.get("cpu"), 0) or 0, x.get("memoria_mb", 0)), reverse=True)
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


# =========================================================
# HTML
# =========================================================

def row_html(name: str, value: str, min_value: str = "-", max_value: str = "-") -> str:
    return f"""
    <div class="metric-row">
        <div class="sensor-name"><span class="small-square"></span>{esc(name)}</div>
        <div>{esc(value)}</div>
        <div>{esc(min_value)}</div>
        <div>{esc(max_value)}</div>
    </div>
    """


def section_icon_for_title(icon: str, title: str, extra: str = "") -> str:
    title_upper = str(title).upper()
    extra_upper = str(extra).upper()

    if "MEMÓRIA" in title_upper or "MEMORIA" in title_upper:
        return icon_img("memoria", "section-svg")

    if "USO DA REDE" in title_upper:
        return icon_img("uso_rede", "section-svg")

    if "QUALIDADE" in title_upper and "REDE" in title_upper:
        return icon_img("qualidade_rede", "section-svg")

    if "DRIVER" in extra_upper:
        return icon_img("gpu", "section-svg")

    if (
        "CPU" in title_upper
        or "RYZEN" in title_upper
        or "CORE" in title_upper
        or "PROCESSOR" in title_upper
    ):
        return icon_img("cpu", "section-svg")

    # Fallback: mantém o símbolo antigo se não houver ícone mapeado.
    return f"<span>{esc(icon)}</span>"


def section_title(icon: str, title: str, extra: str = "") -> str:
    extra_html = f"<span class='section-extra'>{esc(extra)}</span>" if extra else ""
    return f"""
    <div class="section-title">
        <span class="section-icon">{section_icon_for_title(icon, title, extra)}</span>
        <span>{esc(title)}</span>
        {extra_html}
    </div>
    """


def render_network_page(snapshot: Dict[str, Any]) -> str:
    network = snapshot.get("network", {}) or {}

    download_atual = network.get("download_mbps", snapshot.get("download_mbps", 0))
    upload_atual = network.get("upload_mbps", snapshot.get("upload_mbps", 0))
    ping_atual = network.get("ping", snapshot.get("ping"))
    packet_loss_atual = network.get("packet_loss", snapshot.get("packet_loss"))
    jitter_atual = network.get("jitter", snapshot.get("jitter"))

    # Velocidade de link. Se o módulo de rede futuramente trouxer estes campos,
    # o card já usa automaticamente. Por enquanto fica com fallback 100/100 Mbps.
    download_link = network.get("download_link_mbps", network.get("link_download_mbps", 100))
    upload_link = network.get("upload_link_mbps", network.get("link_upload_mbps", 100))

    def network_row(name: str, link: str, atual: str, percent: str = "--") -> str:
        return f"""
        <div class="network-row">
            <div class="sensor-name"><span class="small-square"></span>{esc(name)}</div>
            <div>{esc(link)}</div>
            <div>{esc(atual)}</div>
            <div>{esc(percent)}</div>
        </div>
        """

    return f"""
    <div class="monitor-page" data-page="rede">
        <div class="network-head">
            <div>SENSOR</div><div>LINK</div><div>ATUAL</div><div>%</div>
        </div>

        {section_title("◉", "USO DA REDE")}
        {network_row("DOWNLOAD", fmt_num(download_link, "Mbps", 0), fmt_mbps(download_atual), "--")}
        {network_row("UPLOAD", fmt_num(upload_link, "Mbps", 0), fmt_mbps(upload_atual), "--")}

        {section_title("▥", "QUALIDADE DA REDE")}
        {network_row("PING", "--", fmt_num(ping_atual, "ms", 1), "--")}
        {network_row("PACKET LOSS", "--", fmt_percent(packet_loss_atual), "--")}
        {network_row("JITTER", "--", fmt_num(jitter_atual, "ms", 2), "--")}
    </div>
    """


def render_monitor_card(snapshot: Dict[str, Any]) -> str:
    ram_min, ram_max = minmax_from_history("ram_used_gb")
    gpu_min, gpu_max = minmax_from_history("gpu_percent")
    gpu_mem_min, gpu_mem_max = minmax_from_history("gpu_memory_percent")
    temp_min, temp_max = minmax_from_history("gpu_temp")
    cpu_min, cpu_max = minmax_from_history("cpu_percent")

    memoria = snapshot["memory"]
    gpu = snapshot["gpu"]
    gpu_name = str(snapshot.get("gpu_name") or "GPU")
    driver = str(snapshot.get("gpu_driver") or "--")
    cpu_name = str(snapshot.get("cpu_name") or "CPU")

    monitor_rows = [
        """
        <div class="monitor-page is-active" data-page="monitor">
            <div class="metric-head">
                <div>SENSOR</div><div>VALOR</div><div>MIN</div><div>MAX</div>
            </div>
        """,
        section_title("▦", "MEMÓRIA e DISCO"),
        row_html("MEMÓRIA RAM", fmt_gb(memoria.get("used")), fmt_gb(ram_min), fmt_gb(ram_max)),
    ]

    for disk in snapshot["disks"][:2]:
        monitor_rows.append(row_html(str(disk.get("nome", "DISCO")), fmt_percent(disk.get("percent")), "-", "-"))

    monitor_rows.extend(
        [
            section_title("◉", gpu_name, f"Driver {driver}"),
            row_html("USO GPU", fmt_percent(gpu.get("uso_gpu")), fmt_percent(gpu_min), fmt_percent(gpu_max)),
            row_html("MEMÓRIA GPU", fmt_percent(gpu.get("uso_memoria_gpu")), fmt_percent(gpu_mem_min), fmt_percent(gpu_mem_max)),
            row_html("TEMPERATURA", f"{fmt_num(gpu.get('temperatura'), '°C', 0)}", f"{fmt_num(temp_min, '°C', 0)}", f"{fmt_num(temp_max, '°C', 0)}"),
        ]
    )

    # Exibição de memória GPU:
    # - iGPU/APU: mostra memória total, usada, compartilhada e dedicada.
    # - GPU dedicada: mostra VRAM total, usada e livre.
    if gpu.get("usa_memoria_compartilhada"):
        monitor_rows.extend(
            [
                row_html("MEM. GPU TOTAL", fmt_gb(gpu.get("memoria_total_gb")), "-", "-"),
                row_html("MEM. GPU USADA", fmt_gb(gpu.get("memoria_usada_gb")), "-", "-"),
                row_html("MEM. COMPARTILHADA", fmt_gb(gpu.get("memoria_compartilhada_gb")), "-", "-"),
            ]
        )

        if gpu.get("memoria_dedicada_gb") != "N/A":
            monitor_rows.append(row_html("MEM. DEDICADA", fmt_gb(gpu.get("memoria_dedicada_gb")), "-", "-"))
    else:
        monitor_rows.extend(
            [
                row_html("VRAM TOTAL", fmt_gb(gpu.get("memoria_total_gb")), "-", "-"),
                row_html("VRAM USADA", fmt_gb(gpu.get("memoria_usada_gb")), "-", "-"),
                row_html("VRAM LIVRE", fmt_gb(gpu.get("memoria_livre_gb")), "-", "-"),
            ]
        )

    monitor_rows.extend(
        [
            row_html("CLOCK GPU", f"{fmt_num(gpu.get('clock_gpu'), ' MHz', 0)}", "--", "--"),
            row_html("CLOCK MEMÓRIA", f"{fmt_num(gpu.get('clock_memoria'), ' MHz', 0)}", "--", "--"),
            section_title("◉", cpu_name),
            row_html("USO CPU", fmt_percent(snapshot.get("cpu_percent")), fmt_percent(cpu_min), fmt_percent(cpu_max)),
            "</div>",
        ]
    )

    return f"""
    <div class="monitor-card card" id="monitor-card" data-monitor-icon="{esc(icon_img('monitor', 'title-svg'))}" data-rede-icon="{esc(icon_img('rede', 'title-svg'))}">
        <div class="card-title">
            <div>
                <span class="title-icon" id="monitor-title-icon">{icon_img("monitor", "title-svg")}</span>
                <span id="monitor-title-text">MONITOR</span>
            </div>
            <button class="monitor-page-btn" id="monitor-page-btn" type="button" title="Alternar página">›</button>
        </div>
        <div class="divider"></div>

        <div class="monitor-carousel">
            <div class="monitor-pages" id="monitor-pages">
                {''.join(monitor_rows)}
                {render_network_page(snapshot)}
            </div>
        </div>
    </div>
    """


def render_process_card(snapshot: Dict[str, Any]) -> str:
    rows = [
        f"""
        <div class="process-card card">
            <div class="card-title">
                <div><span class="title-icon">{icon_img("processos", "title-svg")}</span> PROCESSOS</div>
            </div>
            <div class="divider"></div>
            <div class="process-head">
                <div>NOME</div><div>CPU</div><div>RAM</div><div>THREADS</div>
            </div>
        """
    ]

    for proc in snapshot["processes"][:10]:
        name = str(proc.get("nome", "--"))
        if len(name) > 18:
            name = name[:15] + "..."

        rows.append(
            f"""
            <div class="process-row">
                <div class="sensor-name"><span class="small-square"></span>{esc(name)}</div>
                <div>{esc(fmt_percent(proc.get("cpu")))}</div>
                <div>{esc(fmt_num(proc.get("memoria_mb"), " MB", 2))}</div>
                <div>{esc(proc.get("threads", "--"))}</div>
            </div>
            """
        )

    rows.append("</div>")
    return "".join(rows)


def render_chat_card() -> str:
    return f"""
    <div class="chat-card card">
        <div class="card-title"><div><span class="title-icon">{icon_img("chatbot", "title-svg")}</span> CHATBOT</div></div>

        <div id="chat-messages" class="chat-messages">
            <div class="chat-bubble bot">
                Olá! Posso ajudar a interpretar os dados do monitoramento.
            </div>
        </div>

        <div id="chat-form" class="chat-input-row">
            <input id="chat-input" class="chat-input" type="text" placeholder="DIGITE AQUI..." autocomplete="off" />
            <button id="chat-send" class="chat-send" type="button" title="Enviar">{icon_img("chatbot_enviar", "send-svg")}</button>
        </div>
    </div>
    """



def build_yaxis_ticks(values: List[float], suffix: str):
    """
    Cria tickvals/ticktext para o eixo Y.
    Evita o bug visual em que o Plotly mostra só "Mbps" sem o número.
    """
    clean_values = [safe_float(v, None) for v in values]
    clean_values = [float(v) for v in clean_values if v is not None]

    if not clean_values:
        clean_values = [0.0]

    max_value = max(clean_values)
    min_value = min(clean_values)

    if max_value == min_value:
        max_value = max_value + 1

    # Para porcentagem, mantém uma escala amigável.
    if suffix == "%":
        upper = max(100, max_value)
        tickvals = [0, 20, 40, 60, 80, 100] if upper <= 100 else [0, upper * .25, upper * .5, upper * .75, upper]
    else:
        upper = max_value

        if upper <= 0:
            upper = 1

        tickvals = [0, upper * .25, upper * .5, upper * .75, upper]

    def tick_label(v):
        if suffix == "%":
            return f"{fmt_num(v, '', 0)}%"
        if suffix.strip() == "Mbps":
            return f"{fmt_num(v, '', 1)}M"
        if suffix.strip() == "ms":
            return f"{fmt_num(v, '', 0)}ms"
        return f"{fmt_num(v, '', 1)}{suffix}"

    ticktext = [tick_label(v) for v in tickvals]
    return tickvals, ticktext



def make_plotly_line_chart(points: List[Any], label: str, suffix: str = "%", max_points: int = 80, include_js: bool = False) -> str:
    """
    Cria um gráfico Plotly em HTML para ser usado dentro do components.html().
    Mantém o visual do card antigo, mas com Plotly.
    """
    values = []
    labels = []

    for idx, item in enumerate(st.session_state.get("history", [])[-max_points:]):
        value = safe_float(item.get(points), None)

        if value is None:
            continue

        values.append(float(value))

        ts = item.get("timestamp")
        labels.append(ts.strftime("%H:%M:%S") if hasattr(ts, "strftime") else str(idx + 1))

    if len(values) < 2:
        return f"""
        <div class="mini-chart">
            <div class="mini-chart-header">
                <span>{esc(label)}</span>
                <strong>--{esc(suffix)}</strong>
            </div>
            <div class="empty-chart">Aguardando histórico...</div>
        </div>
        """

    last_value = values[-1]
    min_label = fmt_num(min(values), suffix, 1)
    max_label = fmt_num(max(values), suffix, 1)
    last_label = fmt_num(last_value, suffix, 1)

    tickvals, ticktext = build_yaxis_ticks(values, suffix)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=labels,
            y=values,
            mode="lines",
            line=dict(color="#E84E62", width=2.4, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(232, 78, 98, 0.13)",
            hovertemplate=f"{label}: %{{y:.2f}}{suffix}<extra></extra>",
        )
    )

    fig.update_layout(
        autosize=True,
        margin=dict(l=48, r=8, t=4, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F9FC",
        font=dict(color="#374957", size=10, family="Segoe UI"),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, automargin=True),
        yaxis=dict(
            showgrid=True,
            gridcolor="#DDE5EE",
            zeroline=False,
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            tickfont=dict(size=10, color="#374957"),
            automargin=True,
        ),
        hovermode="x unified",
        showlegend=False,
    )

    fig.update_xaxes(showline=True, linewidth=1, linecolor="#C8D1DC")
    fig.update_yaxes(showline=True, linewidth=1, linecolor="#C8D1DC")

    plot_html = fig.to_html(
        full_html=False,
        include_plotlyjs=True if include_js else False,
        config={"displayModeBar": False, "responsive": True},
        default_width="100%",
        default_height="100%",
    )

    return f"""
    <div class="mini-chart">
        <div class="mini-chart-header">
            <span>{esc(label)}</span>
            <strong>{esc(last_label)}</strong>
        </div>

        <div class="plotly-mini">
            {plot_html}
        </div>

        <div class="chart-minmax">
            <span>MIN {esc(min_label)}</span>
            <span>MAX {esc(max_label)}</span>
        </div>
    </div>
    """


def history_values(key: str) -> List[Any]:
    return [item.get(key) for item in st.session_state.get("history", [])]



def render_graph_card() -> str:
    chart_specs = [
        ("cpu_percent", "CPU", "%"),
        ("ram_percent", "MEMÓRIA RAM", "%"),
        ("gpu_percent", "GPU", "%"),
        ("gpu_memory_percent", "MEMÓRIA GPU", "%"),
        ("download_mbps", "DOWNLOAD", " Mbps"),
        ("upload_mbps", "UPLOAD", " Mbps"),
        ("ping", "PING", " ms"),
        ("jitter", "JITTER", " ms"),
    ]

    charts = []

    for index, (key, label, suffix) in enumerate(chart_specs):
        charts.append(make_plotly_line_chart(key, label, suffix, include_js=(index == 0)))

    return f"""
    <div class="graph-card card">
        <div class="card-title"><div><span class="title-icon">{icon_img("graficos", "title-svg")}</span> GRÁFICOS</div></div>
        <div class="charts-grid">
            {''.join(charts)}
        </div>
    </div>
    """

def render_page(snapshot: Dict[str, Any]) -> str:
    return render_template(
        "./index.html",
        CHAT_CARD=render_chat_card(),
        MONITOR_CARD=render_monitor_card(snapshot),
        PROCESS_CARD=render_process_card(snapshot),
        GRAPH_CARD=render_graph_card(),
    )


# =========================================================
# Página
# =========================================================


st.set_page_config(
    page_title=APP_NAME,
    page_icon="⌁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Autorefresh automático desativado para evitar loop de rerun.
# Com REFRESH_MS = 0, o histórico só atualiza ao abrir/recarregar a página.
if st_autorefresh is not None and REFRESH_MS > 0:
    st_autorefresh(interval=REFRESH_MS, key="unaboard_auto_refresh")

# A cada refresh/rerun do Streamlit:
# 1. coleta os dados atuais;
# 2. registra no historico/historico.json;
# 3. usa o mesmo snapshot nos cards MONITOR, REDE e PROCESSOS.
snapshot = register_streamlit_refresh_history()


st.markdown(
    f"""
<style>
{load_text("assets/css/streamlit_host.css")}
</style>
""",
    unsafe_allow_html=True,
)


DASHBOARD_CSS = f"""
<meta name="color-scheme" content="light only">
<style>
{load_text("assets/css/dashboard.css")}
</style>

<style>
{load_text("assets/css/responsive.css")}
</style>
"""

DASHBOARD_JS = load_js_scripts(
    [
        "assets/js/core.js",
        "assets/js/animacao.js",
        "assets/js/responsivo.js",
        "assets/js/monitor.js",
        "assets/js/chatbot.js",
        "assets/js/app.js",
    ]
)

components.html(DASHBOARD_CSS + render_page(snapshot) + DASHBOARD_JS, height=1, scrolling=False)


