import psutil
import time

from dados.cpu import get_cpu
from dados.disco import get_disco
# from dados.gpu import get_gpu ----- A VALIDAR ------
from dados.memoria import get_memoria
from dados.rede import get_rede
from dados.processos import get_processos

while True:

    cpu = get_cpu()
    disco = get_disco()
    memoria = get_memoria()
    rede = get_rede()
    processos = get_processos()

    print("=" * 50)

    print(f"CPU: {cpu}%")

    print(f"RAM: {memoria['percent']}%")
    print(f"RAM usada: {memoria['used']} GB")

    print(f"DISCO: {disco['percent']}%")

    print(f"UPLOAD: {rede['bytes_sent']} bytes")
    print(f"DOWNLOAD: {rede['bytes_recv']} bytes")

    print("\nPROCESSOS MAIS PESADOS:")

    for proc in processos:

        print(
            f"{proc['nome']} | "
            f"CPU: {proc['cpu']}% | "
            f"RAM: {proc['memoria']}%"
        )

    time.sleep(2)