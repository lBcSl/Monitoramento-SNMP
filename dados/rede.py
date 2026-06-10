import psutil
import time

ultima_leitura = psutil.net_io_counters()
ultimo_tempo = time.time()

def get_rede():

    global ultima_leitura 
    global ultimo_tempo

    atual = psutil.net_io_counters()
    tempo_atual = time.time()

    intervalo = tempo_atual - ultimo_tempo

    download_bytes = atual.bytes_recv - ultima_leitura.bytes_recv
    upload_bytes = atual.bytes_sent - ultima_leitura.bytes_sent

    download_mbps = round(
        (download_bytes * 8) / intervalo / 1_000_000,
        2
    )

    upload_mbps = round(
        (upload_bytes * 8) / intervalo / 1_000_000,
        2
    )

    ultima_leitura = atual
    ultimo_tempo = tempo_atual

    return {
        "download_mbps": download_mbps,
        "upload_mbps": upload_mbps,
        "bytes_recv_total": atual.bytes_recv,
        "bytes_sent_total": atual.bytes_sent
    }