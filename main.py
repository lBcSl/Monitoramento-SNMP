import psutil
import time
import os

from datetime import datetime
from source.dados.cpu import get_cpu
from source.dados.disco import get_disco
from source.dados.gpu import get_gpu
from source.dados.memoria import get_memoria
from source.dados.processos import get_processos
from source.dados.rede import get_rede
from source.dados.rede_qualidade import (get_ping, get_packet_loss, get_jitter)
from source.historico.salvar import salvar_historico

while True:

    cpu = get_cpu()
    gpu = get_gpu()
    disco = get_disco()
    memoria = get_memoria()
    rede = get_rede()
    processos = get_processos()
    ping = get_ping()
    loss = get_packet_loss()
    jitter = get_jitter()

    dados = {

        "cpu": cpu,

        "ram_percent": memoria["percent"],

        "ram_gb": memoria["used"],

        "disco_percent": disco["percent"],

        "download_mbps": rede["download_mbps"],

        "upload_mbps": rede["upload_mbps"],

        "ping": ping,

        "packet_loss": loss,

        "jitter": jitter,

        "gpu_percent": gpu["uso_gpu"],

        "gpu_temp": gpu["temperatura"],

        "vram_usada": gpu["memoria_usada_gb"]

    }

    salvar_historico(dados)

    os.system("cls") # LIMPAR A CLI
    data_agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S") # MOSTRAR A DATA
    print("=" * 50)

    print("\n===== CPU: =====")

    print(f"CPU: {cpu}%")

    print("\n===== MEMÓRIA e DISCO: ===== ")

    print(f"RAM: {memoria['percent']}%")
    print(f"RAM usada: {memoria['used']} GB")
    print(f"DISCO: {disco['percent']}%")

    print(f"\n===== REDE =====")

    print(f"Download: {rede['download_mbps']} Mbps")
    print(f"Upload: {rede['upload_mbps']} Mbps")

    print("\n===== QUALIDADE DA REDE =====")

    print(f"Ping: {ping} ms")

    print(f"Packet Loss: {loss}%")

    print(f"Jitter: {jitter} ms")

    print("\n===== GPU =====")

    print(f"Modelo: {gpu['nome']}")
    print(f"Uso GPU: {gpu['uso_gpu']}%")
    print(f"Uso Memória GPU: {gpu['uso_memoria_gpu']}%")
    print(f"Temperatura: {gpu['temperatura']}°C")
    if gpu["usa_memoria_compartilhada"]:
        print(f"Memória GPU Total: {gpu['memoria_total_gb']} GB")
        print(f"Memória GPU Usada: {gpu['memoria_usada_gb']} GB")
        print(f"Memória Compartilhada: {gpu['memoria_compartilhada_gb']} GB")

        if gpu["memoria_dedicada_gb"] != "N/A":
            print(f"Memória Dedicada: {gpu['memoria_dedicada_gb']} GB")
    else:
        print(f"VRAM Total: {gpu['memoria_total_gb']} GB")
        print(f"VRAM Usada: {gpu['memoria_usada_gb']} GB")
        print(f"VRAM Livre: {gpu['memoria_livre_gb']} GB")

    print("\n===== TOP PROCESSOS =====")
    for proc in processos:

        print(
        f"{proc['nome']} | "
        f"CPU: {proc['cpu']}% | "
        f"RAM: {proc['memoria_mb']} MB | "
        f"Threads: {proc['threads']}"
    )

    print(f"\nData do monitoramento: {data_agora}")

    time.sleep(5)