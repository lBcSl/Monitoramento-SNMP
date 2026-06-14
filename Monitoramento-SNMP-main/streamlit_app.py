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
from chatbot import enviar_mensagem_com_hardware

from __future__ import annotations

import html
import math
import platform
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import psutil
import streamlit as st
import streamlit.components.v1 as components

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
REFRESH_MS = 5000
MAX_HISTORY = 80


# =========================================================
# Helpers
# =========================================================

def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def safe_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if value is None or value == "N/A" or value == "--":
            return default
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


@st.cache_data(ttl=5, show_spinner=False)
def collect_snapshot_cached() -> Dict[str, Any]:
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


def section_title(icon: str, title: str, extra: str = "") -> str:
    extra_html = f"<span class='section-extra'>{esc(extra)}</span>" if extra else ""
    return f"""
    <div class="section-title">
        <span class="section-icon">{icon}</span>
        <span>{esc(title)}</span>
        {extra_html}
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

    # Para iGPU Intel sem dedicada real, o total correto é a memória compartilhada.
    dedicated_total = safe_float(gpu.get("memoria_dedicada_total_gb"), None)
    shared_total = safe_float(gpu.get("memoria_compartilhada_total_gb"), None)
    shared_used = safe_float(gpu.get("memoria_compartilhada_gb"), None)

    gpu_is_integrated_without_dedicated = dedicated_total is None or dedicated_total <= 0

    if gpu_is_integrated_without_dedicated and shared_total is not None:
        gpu_total_display = shared_total
        gpu_used_display = shared_used if shared_used is not None else gpu.get("memoria_usada_gb")
        memory_gpu_value = fmt_gb_pair(gpu_used_display, gpu_total_display)
    else:
        memory_gpu_value = fmt_percent(gpu.get("uso_memoria_gpu"))

    rows = [
        """
        <div class="monitor-card card">
            <div class="card-title">
                <div><span class="title-icon">▣</span> MONITOR</div>
                <div class="title-arrow">›</div>
            </div>
            <div class="divider"></div>
            <div class="metric-head">
                <div>SENSOR</div><div>VALOR</div><div>MIN</div><div>MAX</div>
            </div>
        """,
        section_title("▦", "MEMÓRIA e DISCO"),
        row_html("MEMÓRIA RAM", fmt_gb(memoria.get("used")), fmt_gb(ram_min), fmt_gb(ram_max)),
    ]

    for disk in snapshot["disks"][:2]:
        rows.append(row_html(str(disk.get("nome", "DISCO")), fmt_percent(disk.get("percent")), "-", "-"))

    rows.extend(
        [
            section_title("◉", gpu_name, f"Driver {driver}"),
            row_html("USO GPU", fmt_percent(gpu.get("uso_gpu")), fmt_percent(gpu_min), fmt_percent(gpu_max)),
            row_html("MEMÓRIA GPU", memory_gpu_value, fmt_percent(gpu_mem_min), fmt_percent(gpu_mem_max)),
            row_html("TEMPERATURA", f"{fmt_num(gpu.get('temperatura'), '°C', 0)}", f"{fmt_num(temp_min, '°C', 0)}", f"{fmt_num(temp_max, '°C', 0)}"),
        ]
    )

    if gpu_is_integrated_without_dedicated and shared_total is not None:
        rows.extend(
            [
                row_html("MEM. COMPARTILHADA", fmt_gb_pair(gpu.get("memoria_compartilhada_gb"), gpu.get("memoria_compartilhada_total_gb")), "-", "-"),
                row_html("MEM. DEDICADA", "--", "-", "-"),
            ]
        )
    else:
        rows.extend(
            [
                row_html("VRAM TOTAL", fmt_gb(gpu.get("memoria_dedicada_total_gb") if dedicated_total and dedicated_total > 0 else gpu.get("memoria_total_gb")), "-", "-"),
                row_html("VRAM USADA", fmt_gb(gpu.get("memoria_dedicada_gb") if dedicated_total and dedicated_total > 0 else gpu.get("memoria_usada_gb")), "-", "-"),
                row_html("VRAM LIVRE", fmt_gb(gpu.get("memoria_livre_gb")), "-", "-"),
            ]
        )

    rows.extend(
        [
            row_html("CLOCK GPU", f"{fmt_num(gpu.get('clock_gpu'), ' MHz', 0)}", "--", "--"),
            row_html("CLOCK MEMÓRIA", f"{fmt_num(gpu.get('clock_memoria'), ' MHz', 0)}", "--", "--"),
            section_title("◉", cpu_name),
            row_html("USO CPU", fmt_percent(snapshot.get("cpu_percent")), fmt_percent(cpu_min), fmt_percent(cpu_max)),
            "</div>",
        ]
    )

    return "".join(rows)


def render_process_card(snapshot: Dict[str, Any]) -> str:
    rows = [
        """
        <div class="process-card card">
            <div class="card-title">
                <div><span class="title-icon">▦</span> PROCESSOS</div>
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
        <div class="card-title"><div><span class="title-icon">◔</span> CHATBOT</div></div>
        <div class="chat-space"></div>
        <div class="fake-input">
            <span>DIGITE AQUI...</span>
            <span class="send-icon">⌲</span>
        </div>
    </div>
    """


def render_graph_card() -> str:
    return """
    <div class="graph-card card">
        <div class="card-title"><div><span class="title-icon">▣</span> GRÁFICOS</div></div>
    </div>
    """


def render_page(snapshot: Dict[str, Any]) -> str:
    return f"""
    <div class="topbar">
        <div class="brand">
            <span class="brand-mark">〉</span>
            <span>UNABOARD</span>
        </div>

        <div class="user-box">
            <span>{esc(USER_NAME)}</span>
            <span class="avatar"></span>
            <span class="down-arrow">▾</span>
        </div>
    </div>

    <main class="dashboard-wrap">
        <div class="dashboard-grid">
            {render_chat_card()}

            <div class="middle-stack">
                {render_monitor_card(snapshot)}
                {render_process_card(snapshot)}
            </div>

            {render_graph_card()}
        </div>
    </main>
    """


# =========================================================
# Página
# =========================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⌁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if st_autorefresh:
    st_autorefresh(interval=REFRESH_MS, key="unaboard_refresh")

if "history" not in st.session_state:
    st.session_state.history = []

snapshot = collect_snapshot_cached()
st.session_state.history.append(snapshot)
st.session_state.history = st.session_state.history[-MAX_HISTORY:]


st.markdown("""
<style>
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    footer,
    #MainMenu {
        display: none !important;
    }

    .block-container {
        padding: 0 !important;
        max-width: none !important;
    }

    .stApp {
        background: #DDE2E7;
    }

    iframe {
        display: block;
        width: 100%;
        opacity: 1 !important;
        filter: none !important;
    }
</style>
""", unsafe_allow_html=True)

CSS = """
    <meta name="color-scheme" content="light only">
    <style>
        :root {
            color-scheme: light !important;

            /* Paleta com mais contraste */
            --bg: #DCE2E8;
            --card: #FFFFFF;
            --text: #1B2A41;
            --muted: #4F5E72;
            --border: #AEB9C6;
            --shadow: 0 10px 26px rgba(27, 42, 65, 0.22);
            --soft-shadow: 0 6px 18px rgba(27, 42, 65, 0.16);
            --red: #E84E62;
        }

        * {
            box-sizing: border-box;
        }

        html, body, [class*="css"] {
            font-family: "Segoe UI", Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }

        html, body {
            color-scheme: light !important;
        }

        body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            overflow: hidden;
            opacity: 1 !important;
            filter: none !important;
            -webkit-font-smoothing: antialiased;
            text-rendering: geometricPrecision;
        }

        body * {
            filter: none !important;
        }

        .topbar {
            height: 72px;
            background: #FFFFFF;
            border-bottom: 1px solid #B9C3D0;
            box-shadow: 0 8px 24px rgba(35, 45, 55, 0.20);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 34px 0 40px;
            color: #0A0D13;
            opacity: 1 !important;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 23px;
            font-weight: 600;
            letter-spacing: 1.2px;
            color: #05070A !important;
        }

        .brand-mark {
            color: var(--red);
            font-size: 34px;
            line-height: 1;
            font-weight: 300;
            transform: scaleX(.72);
            display: inline-block;
        }

        .user-box {
            display: flex;
            align-items: center;
            gap: 11px;
            font-size: 20px;
            font-weight: 600;
            letter-spacing: .8px;
            color: #18263E;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: inline-block;
            background:
                radial-gradient(circle at 65% 30%, #FBE0D8 0 18%, transparent 19%),
                radial-gradient(circle at 45% 45%, #1F1620 0 24%, transparent 25%),
                linear-gradient(135deg, #090B12 0 42%, #D74A57 43% 100%);
            box-shadow: inset 0 0 0 2px rgba(255,255,255,.65);
        }

        .down-arrow {
            color: #23314A;
            font-size: 16px;
            margin-left: 2px;
        }

        .dashboard-wrap {
            padding: 32px 32px 34px 32px;
            min-height: calc(100vh - 72px);
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: 330px 475px minmax(500px, 1fr);
            gap: 22px;
            min-height: calc(100vh - 138px);
        }

        .middle-stack {
            display: grid;
            grid-template-rows: 445px minmax(0, 1fr);
            gap: 22px;
            min-height: calc(100vh - 138px);
        }

        .card {
            background: var(--card);
            border-radius: 8px;
            border: 1px solid rgba(171, 184, 199, .98);
            box-shadow: var(--shadow);
            color: var(--text);
            opacity: 1 !important;
        }

        .chat-card,
        .graph-card {
            min-height: calc(100vh - 138px);
        }

        .chat-card {
            padding: 22px 16px 16px 16px;
            display: flex;
            flex-direction: column;
        }

        .chat-space {
            flex: 1;
        }

        .fake-input {
            height: 31px;
            width: 100%;
            border: 1px solid #E0E5EC;
            border-radius: 999px;
            box-shadow: inset 0 1px 2px rgba(0,0,0,.04), 0 2px 8px rgba(0,0,0,.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 11px 0 16px;
            font-size: 10px;
            font-weight: 600;
            color: #8290A1;
            letter-spacing: .2px;
        }

        .send-icon {
            font-size: 18px;
            color: #26344D;
            line-height: 1;
        }

        .monitor-card {
            padding: 18px 18px 14px 18px;
            overflow: hidden;
        }

        .process-card {
            padding: 18px 18px 14px 18px;
            overflow: hidden;
        }

        .graph-card {
            padding: 22px 18px 18px 18px;
        }

        .card-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 18px;
            font-weight: 600;
            letter-spacing: 1.1px;
            color: var(--text);
        }

        .title-icon {
            font-size: 22px;
            margin-right: 9px;
            color: var(--text);
            vertical-align: -1px;
        }

        .title-arrow {
            color: var(--text);
            font-size: 31px;
            font-weight: 300;
            line-height: 1;
            margin-top: -2px;
        }

        .divider {
            height: 1px;
            background: var(--border);
            margin: 14px 0 13px 0;
        }

        .metric-head,
        .metric-row {
            display: grid;
            grid-template-columns: 1.7fr .72fr .53fr .53fr;
            align-items: center;
            column-gap: 8px;
        }

        .metric-head {
            color: var(--text);
            font-size: 14px;
            font-weight: 600;
            letter-spacing: .9px;
            margin-bottom: 11px;
        }

        .metric-row {
            color: var(--text);
            font-size: 11px;
            line-height: 1.38;
            font-weight: 600;
        }

        .section-title {
            display: flex;
            align-items: center;
            gap: 7px;
            color: var(--text);
            font-size: 12px;
            line-height: 1.1;
            font-weight: 600;
            margin: 10px 0 5px 0;
        }

        .section-icon {
            font-size: 15px;
            width: 16px;
            display: inline-flex;
            justify-content: center;
        }

        .section-extra {
            font-size: 7px;
            color: var(--muted);
            font-weight: 600;
            letter-spacing: 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 135px;
        }

        .sensor-name {
            display: flex;
            align-items: center;
            gap: 7px;
            padding-left: 24px;
            white-space: nowrap;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .small-square {
            width: 7px;
            height: 7px;
            border: 1.35px solid var(--text);
            border-radius: 2px;
            display: inline-block;
            flex: 0 0 auto;
        }

        .process-head,
        .process-row {
            display: grid;
            grid-template-columns: 1.5fr .55fr .85fr .65fr;
            align-items: center;
            column-gap: 10px;
        }

        .process-head {
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }

        .process-row {
            font-size: 11px;
            line-height: 1.45;
            font-weight: 600;
            color: var(--text);
        }

        @media (max-width: 1350px) {
            .dashboard-grid {
                grid-template-columns: 300px 430px minmax(420px, 1fr);
                gap: 18px;
            }

            .middle-stack {
                grid-template-rows: 445px minmax(0, 1fr);
            }

            .card-title {
                font-size: 16px;
            }

            .metric-head {
                font-size: 13px;
            }

            .metric-row,
            .process-row {
                font-size: 10px;
            }
        }
    </style>
    """

components.html(CSS + render_page(snapshot), height=980, scrolling=False)

