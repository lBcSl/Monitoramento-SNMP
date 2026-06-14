"""
diagnostico_gpu_taskmanager_v2.py

Mostra os valores completos dos contadores de GPU, sem truncar como Format-Table.

Uso:
python diagnostico_gpu_taskmanager_v2.py
"""

import subprocess
import json
import re


def run_ps(script):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip()


def section(title):
    print("\n" + "=" * 28)
    print(title)
    print("=" * 28)


section("GPU BASIC INFO")
out, err = run_ps(r"""
Get-CimInstance Win32_VideoController |
Select-Object Name, AdapterRAM, DriverVersion |
ConvertTo-Json -Depth 4
""")
print(out or err or "Sem retorno")


section("GPU ENGINE - JSON")
out, err = run_ps(r"""
(Get-Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 1).CounterSamples |
Sort-Object CookedValue -Descending |
Select-Object -First 40 Path, InstanceName, CookedValue |
ConvertTo-Json -Depth 6
""")
print(out or err or "Sem retorno")


section("GPU MEMORY - JSON")
out, err = run_ps(r"""
$counters = @(
    '\GPU Adapter Memory(*)\Dedicated Usage',
    '\GPU Adapter Memory(*)\Shared Usage',
    '\GPU Adapter Memory(*)\Dedicated Limit',
    '\GPU Adapter Memory(*)\Shared Limit'
)

$result = foreach ($counter in $counters) {
    try {
        (Get-Counter $counter).CounterSamples |
        Select-Object @{n='Counter';e={$counter}}, Path, InstanceName, CookedValue
    } catch {}
}

$result | ConvertTo-Json -Depth 6
""")
print(out or err or "Sem retorno")


section("GPU MEMORY - RESUMO GB")
out, err = run_ps(r"""
function ToGB($bytes) {
    if ($null -eq $bytes) { return 0 }
    return [math]::Round(($bytes / 1GB), 2)
}

$dedUsage = ((Get-Counter '\GPU Adapter Memory(*)\Dedicated Usage').CounterSamples | Measure-Object CookedValue -Sum).Sum
$shaUsage = ((Get-Counter '\GPU Adapter Memory(*)\Shared Usage').CounterSamples | Measure-Object CookedValue -Sum).Sum

try { $dedLimit = ((Get-Counter '\GPU Adapter Memory(*)\Dedicated Limit').CounterSamples | Measure-Object CookedValue -Sum).Sum } catch { $dedLimit = 0 }
try { $shaLimit = ((Get-Counter '\GPU Adapter Memory(*)\Shared Limit').CounterSamples | Measure-Object CookedValue -Sum).Sum } catch { $shaLimit = 0 }

if ($shaLimit -eq 0) {
    $shaLimit = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 2
}

[PSCustomObject]@{
    DedicadaUsadaGB = ToGB $dedUsage
    CompartilhadaUsadaGB = ToGB $shaUsage
    TotalUsadoGB = ToGB ($dedUsage + $shaUsage)
    DedicadaTotalGB = ToGB $dedLimit
    CompartilhadaTotalGB = ToGB $shaLimit
    TotalGPUExibivelGB = ToGB ($dedLimit + $shaLimit)
} | ConvertTo-Json -Depth 4
""")
print(out or err or "Sem retorno")
