"""
dados/gpu.py - v6

Compatível com:
- NVIDIA: usa NVML/pynvml.
- AMD Radeon Vega 7 / iGPU: usa contadores do Windows parecidos com o Gerenciador de Tarefas.

Melhorias v6:
- Agrupa os GPU Engines por tipo e SOMA os valores por engine.
- Uso GPU = maior engine agregado, limitado a 100%.
- Memória compartilhada total usa fallback: metade da RAM do sistema, igual o Gerenciador de Tarefas costuma exibir.
- Memória dedicada total usa AdapterRAM quando o contador Dedicated Limit não existe.
"""

import os
import re
import json
import subprocess
import psutil


# ============================================================
# Helpers
# ============================================================

def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def _to_float(value):
    try:
        if value is None or value == "" or value == "N/A":
            return None
        return float(value)
    except Exception:
        return None


def _bytes_to_gb(value):
    try:
        value = float(value)
        if value <= 0:
            return "N/A"
        return round(value / (1024 ** 3), 2)
    except Exception:
        return "N/A"


def _gb_to_bytes(value_gb):
    try:
        if value_gb == "N/A":
            return 0
        return float(value_gb) * (1024 ** 3)
    except Exception:
        return 0


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _run_powershell_json(script, timeout=20):
    if os.name != "nt":
        return None

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags,
        )

        output = (result.stdout or "").strip()
        if not output:
            return None

        return json.loads(output)

    except Exception:
        return None


def _pick_gpu(rows):
    rows = [r for r in _as_list(rows) if isinstance(r, dict)]
    if not rows:
        return {}

    priority = [
        ("amd", "radeon", "vega"),
        ("nvidia", "geforce", "rtx", "gtx"),
        ("intel", "uhd", "iris"),
    ]

    for group in priority:
        for row in rows:
            text = " ".join(str(v) for v in row.values()).lower()
            if any(key in text for key in group):
                return row

    return rows[0]


def _extract_engine_type(text):
    """
    Extrai o tipo do engine de uma string como:
    pid_123_luid_..._eng_0_engtype_3d
    pid_123_luid_..._eng_7_engtype_video codec 0
    """
    text = str(text).lower()

    match = re.search(r"engtype_([^)\\]+)", text)
    if not match:
        return "Outros"

    raw = match.group(1).strip()

    if "high priority 3d" in raw:
        return "High Priority 3D"
    if "high priority compute" in raw:
        return "High Priority Compute"
    if raw.startswith("3d"):
        return "3D"
    if raw.startswith("copy"):
        return "Copy"
    if raw.startswith("compute"):
        return "Compute"
    if "video decode" in raw:
        return "Video Decode"
    if "video encode" in raw:
        return "Video Encode"
    if "video codec" in raw:
        return "Video Codec"
    if "video jpeg" in raw:
        return "Video JPEG"
    if "security" in raw:
        return "Security"
    if "timer" in raw:
        return "Timer"

    return raw.title()


# ============================================================
# NVIDIA / NVML
# ============================================================

_NVIDIA_AVAILABLE = False
_nvml = None
_nvml_handle = None

try:
    import pynvml as _nvml
    _nvml.nvmlInit()
    _nvml_handle = _nvml.nvmlDeviceGetHandleByIndex(0)
    _NVIDIA_AVAILABLE = True
except Exception:
    _NVIDIA_AVAILABLE = False
    _nvml = None
    _nvml_handle = None


def _get_gpu_nvidia():
    util = _nvml.nvmlDeviceGetUtilizationRates(_nvml_handle)
    memoria = _nvml.nvmlDeviceGetMemoryInfo(_nvml_handle)

    try:
        temperatura = _nvml.nvmlDeviceGetTemperature(_nvml_handle, _nvml.NVML_TEMPERATURE_GPU)
    except Exception:
        temperatura = "N/A"

    try:
        clock_gpu = _nvml.nvmlDeviceGetClockInfo(_nvml_handle, _nvml.NVML_CLOCK_GRAPHICS)
    except Exception:
        clock_gpu = "N/A"

    try:
        clock_memoria = _nvml.nvmlDeviceGetClockInfo(_nvml_handle, _nvml.NVML_CLOCK_MEM)
    except Exception:
        clock_memoria = "N/A"

    try:
        driver = _decode(_nvml.nvmlSystemGetDriverVersion())
    except Exception:
        driver = "N/A"

    total = round(memoria.total / (1024 ** 3), 2)
    usada = round(memoria.used / (1024 ** 3), 2)
    livre = round(memoria.free / (1024 ** 3), 2)
    uso_vram = round((usada / total) * 100, 1) if total else "N/A"

    return {
        "nome": _decode(_nvml.nvmlDeviceGetName(_nvml_handle)),
        "uso_gpu": round(float(util.gpu), 1),
        "uso_memoria_gpu": round(float(util.memory), 1),
        "uso_vram": uso_vram,
        "temperatura": temperatura,
        "memoria_total_gb": total,
        "memoria_usada_gb": usada,
        "memoria_livre_gb": livre,
        "memoria_compartilhada_gb": "N/A",
        "memoria_dedicada_gb": usada,
        "memoria_compartilhada_total_gb": "N/A",
        "memoria_dedicada_total_gb": total,
        "usa_memoria_compartilhada": False,
        "clock_gpu": clock_gpu,
        "clock_memoria": clock_memoria,
        "driver": driver,
        "backend": "NVIDIA NVML",
        "engines": {},
    }


# ============================================================
# Windows / AMD Vega 7 / iGPU
# ============================================================

def _get_gpu_basic_info_windows():
    script = r"""
$items = @()

try {
    $items += Get-CimInstance Win32_VideoController -ErrorAction Stop |
        Select-Object @{n='Fonte';e={'Win32_VideoController'}},
                      Name, AdapterRAM, DriverVersion, PNPDeviceID
} catch {}

try {
    $items += Get-CimInstance Win32_PnPSignedDriver -ErrorAction Stop |
        Where-Object { $_.DeviceClass -eq 'DISPLAY' } |
        Select-Object @{n='Fonte';e={'Win32_PnPSignedDriver'}},
                      @{n='Name';e={$_.DeviceName}},
                      @{n='AdapterRAM';e={$null}},
                      DriverVersion,
                      DeviceID
} catch {}

try {
    $items += Get-PnpDevice -Class Display -Status OK -ErrorAction Stop |
        Select-Object @{n='Fonte';e={'Get-PnpDevice'}},
                      @{n='Name';e={$_.FriendlyName}},
                      @{n='AdapterRAM';e={$null}},
                      @{n='DriverVersion';e={$null}},
                      InstanceId
} catch {}

$items |
    Where-Object { $_.Name -and $_.Name.Trim() -ne "" } |
    ConvertTo-Json -Compress -Depth 6
"""
    rows = _run_powershell_json(script)
    return _pick_gpu(rows)


def _get_counter_samples(counter_path):
    script = rf"""
try {{
    (Get-Counter -Counter '{counter_path}' -SampleInterval 1 -MaxSamples 1 -ErrorAction Stop).CounterSamples |
        Select-Object Path, InstanceName, CookedValue |
        ConvertTo-Json -Compress -Depth 5
}} catch {{
    $null | ConvertTo-Json -Compress
}}
"""
    return _as_list(_run_powershell_json(script, timeout=25))


def _get_gpu_engine_usage_taskmanager_style():
    samples = _get_counter_samples(r"\GPU Engine(*)\Utilization Percentage")

    if not samples:
        script = r"""
$engines = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue |
    Select-Object Name, UtilizationPercentage
$engines | ConvertTo-Json -Compress -Depth 4
"""
        rows = _as_list(_run_powershell_json(script))
        samples = [
            {"InstanceName": row.get("Name", ""), "CookedValue": row.get("UtilizationPercentage", 0)}
            for row in rows
        ]

    engines = {}

    for sample in samples:
        text = str(sample.get("InstanceName") or sample.get("Path") or "")
        value = _to_float(sample.get("CookedValue"))
        if value is None:
            continue

        engine_name = _extract_engine_type(text)
        engines[engine_name] = engines.get(engine_name, 0.0) + value

    # Remove engines que não costumam entrar no uso visível.
    engines.pop("Timer", None)
    engines.pop("Security", None)

    if not engines:
        return "N/A", {}

    # Cap em 100 por engine, porque a soma por processos pode passar um pouco.
    engines = {k: round(min(v, 100.0), 1) for k, v in engines.items()}

    # O Gerenciador de Tarefas costuma usar o maior engine ativo como "Utilização".
    overall = max(engines.values())

    return round(overall, 1), dict(sorted(engines.items(), key=lambda item: item[1], reverse=True))


def _sum_counter_values(counter_name):
    samples = _get_counter_samples(rf"\GPU Adapter Memory(*)\{counter_name}")
    total = 0.0
    found = False

    for sample in samples:
        value = _to_float(sample.get("CookedValue"))
        if value is not None:
            total += value
            found = True

    return total if found else None


def _get_gpu_memory_taskmanager_style(adapter_ram=None):
    dedicated_usage = _sum_counter_values("Dedicated Usage")
    shared_usage = _sum_counter_values("Shared Usage")
    dedicated_limit = _sum_counter_values("Dedicated Limit")
    shared_limit = _sum_counter_values("Shared Limit")

    # Fallback WMI para usage.
    if dedicated_usage is None and shared_usage is None:
        script = r"""
$mem = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue |
    Select-Object Name, DedicatedUsage, SharedUsage, DedicatedLimit, SharedLimit
$mem | ConvertTo-Json -Compress -Depth 4
"""
        rows = _as_list(_run_powershell_json(script))
        dedicated_usage = 0
        shared_usage = 0
        dedicated_limit = dedicated_limit or 0
        shared_limit = shared_limit or 0

        for row in rows:
            try:
                dedicated_usage += int(row.get("DedicatedUsage", 0) or 0)
                shared_usage += int(row.get("SharedUsage", 0) or 0)
                dedicated_limit += int(row.get("DedicatedLimit", 0) or 0)
                shared_limit += int(row.get("SharedLimit", 0) or 0)
            except Exception:
                pass

    dedicated_usage = dedicated_usage or 0
    shared_usage = shared_usage or 0
    dedicated_limit = dedicated_limit or 0
    shared_limit = shared_limit or 0

    # Fallback dedicado: AdapterRAM costuma ser ~512 MB na Vega 7.
    if dedicated_limit <= 0:
        try:
            dedicated_limit = int(adapter_ram or 0)
        except Exception:
            dedicated_limit = 0

    # Fallback compartilhado: Task Manager normalmente exibe metade da RAM como memória compartilhada.
    if shared_limit <= 0:
        try:
            shared_limit = psutil.virtual_memory().total / 2
        except Exception:
            shared_limit = 0

    total_usage = dedicated_usage + shared_usage
    total_limit = dedicated_limit + shared_limit

    dedicated_used_gb = _bytes_to_gb(dedicated_usage)
    shared_used_gb = _bytes_to_gb(shared_usage)
    dedicated_total_gb = _bytes_to_gb(dedicated_limit)
    shared_total_gb = _bytes_to_gb(shared_limit)
    total_used_gb = _bytes_to_gb(total_usage)
    total_gb = _bytes_to_gb(total_limit)

    used_num = _to_float(total_used_gb)
    total_num = _to_float(total_gb)

    if used_num is not None and total_num is not None and total_num >= used_num:
        free_gb = round(total_num - used_num, 2)
        percent = round((used_num / total_num) * 100, 1) if total_num > 0 else "N/A"
    else:
        free_gb = "N/A"
        percent = "N/A"

    return {
        "usada_gb": total_used_gb,
        "total_gb": total_gb,
        "livre_gb": free_gb,
        "uso_percent": percent,
        "dedicada_usada_gb": dedicated_used_gb,
        "compartilhada_usada_gb": shared_used_gb,
        "dedicada_total_gb": dedicated_total_gb,
        "compartilhada_total_gb": shared_total_gb,
    }


def _get_lhm_sensors_windows():
    script = r"""
$namespaces = @("root\LibreHardwareMonitor", "root\OpenHardwareMonitor")
$result = @()

foreach ($ns in $namespaces) {
    try {
        $sensors = Get-CimInstance -Namespace $ns -ClassName Sensor -ErrorAction Stop |
            Select-Object Name, SensorType, Value, Identifier
        if ($sensors) {
            $result += $sensors
            break
        }
    } catch {}
}

$result | ConvertTo-Json -Compress -Depth 5
"""
    return _as_list(_run_powershell_json(script))


def _find_sensor(sensors, sensor_type, patterns):
    for sensor in sensors:
        stype = str(sensor.get("SensorType", "")).lower()
        name = str(sensor.get("Name", "")).lower()
        identifier = str(sensor.get("Identifier", "")).lower()
        text = f"{name} {identifier}"

        if stype != sensor_type.lower():
            continue

        if any(pattern.lower() in text for pattern in patterns):
            try:
                return round(float(sensor.get("Value")), 1)
            except Exception:
                return "N/A"

    return "N/A"


def _get_gpu_windows():
    info = _get_gpu_basic_info_windows()

    nome = (
        info.get("Name")
        or info.get("FriendlyName")
        or info.get("DeviceName")
        or "GPU não identificada"
    )

    driver = info.get("DriverVersion") or info.get("Driver") or "N/A"
    adapter_ram = info.get("AdapterRAM")

    uso_gpu, engines = _get_gpu_engine_usage_taskmanager_style()
    memoria = _get_gpu_memory_taskmanager_style(adapter_ram=adapter_ram)

    sensores = _get_lhm_sensors_windows()

    temperatura = _find_sensor(
        sensores,
        "Temperature",
        ["gpu", "gfx", "core", "radeon", "vega"]
    )

    clock_gpu = _find_sensor(
        sensores,
        "Clock",
        ["gpu core", "core", "gfx"]
    )

    clock_memoria = _find_sensor(
        sensores,
        "Clock",
        ["gpu memory", "memory", "vram"]
    )

    uso_gpu_lhm = _find_sensor(
        sensores,
        "Load",
        ["gpu core", "gpu total", "d3d", "3d", "core"]
    )

    if uso_gpu_lhm != "N/A":
        uso_gpu = uso_gpu_lhm

    compartilhada_num = _to_float(memoria["compartilhada_usada_gb"])
    tem_memoria_compartilhada = compartilhada_num is not None and compartilhada_num > 0

    return {
        "nome": nome,
        "uso_gpu": uso_gpu,
        "uso_memoria_gpu": memoria["uso_percent"],
        "uso_vram": memoria["uso_percent"],

        "temperatura": temperatura,

        "memoria_total_gb": memoria["total_gb"],
        "memoria_usada_gb": memoria["usada_gb"],
        "memoria_livre_gb": memoria["livre_gb"],

        "memoria_compartilhada_gb": memoria["compartilhada_usada_gb"],
        "memoria_dedicada_gb": memoria["dedicada_usada_gb"],
        "memoria_compartilhada_total_gb": memoria["compartilhada_total_gb"],
        "memoria_dedicada_total_gb": memoria["dedicada_total_gb"],

        "memoria_dedicada_usada_gb": memoria["dedicada_usada_gb"],
        "memoria_compartilhada_usada_gb": memoria["compartilhada_usada_gb"],

        "usa_memoria_compartilhada": tem_memoria_compartilhada,
        "clock_gpu": clock_gpu,
        "clock_memoria": clock_memoria,
        "driver": driver,
        "backend": "Windows Task Manager Counters",
        "engines": engines,
    }


# ============================================================
# API pública
# ============================================================

def get_gpu():
    if _NVIDIA_AVAILABLE:
        return _get_gpu_nvidia()
    return _get_gpu_windows()


def get_processos_gpu():
    processos = []

    if not _NVIDIA_AVAILABLE:
        return processos

    try:
        for proc in _nvml.nvmlDeviceGetGraphicsRunningProcesses(_nvml_handle):
            try:
                processo = psutil.Process(proc.pid)
                processos.append({
                    "pid": proc.pid,
                    "nome": processo.name(),
                    "memoria_gpu_mb": round(proc.usedGpuMemory / (1024 ** 2), 2)
                })
            except Exception:
                pass
    except Exception:
        pass

    return processos


if __name__ == "__main__":
    gpu = get_gpu()
    for chave, valor in gpu.items():
        print(f"{chave}: {valor}")
