import subprocess
import re

def get_ping():

    try:

        resultado = subprocess.check_output(
            ["ping", "177.152.174.16", "-n", "4"],
            text=True
        )

        tempo = re.findall(r"tempo[=<](\d+)ms", resultado)

        if len(tempo) == 0:
            return None

        tempos = [int(t) for t in tempo]

        media = round(sum(tempos) / len(tempos), 2)

        return media

    except Exception:

        return None

# CALCULAR PACKET LOSS
def get_packet_loss():

    try:

        resultado = subprocess.check_output(
            ["ping", "8.8.8.8", "-n", "10"],
            text=True
        )

        perda = re.search(
            r"(\d+)% de perda",
            resultado
        )

        if perda:

            return int(perda.group(1))

        return 0

    except Exception:

        return None

#CALCULAR JITTER
def get_jitter():

    try:

        resultado = subprocess.check_output(
            ["ping", "8.8.8.8", "-n", "10"],
            text=True
        )

        tempos = re.findall(
            r"tempo[=<](\d+)ms",
            resultado
        )

        tempos = [int(t) for t in tempos]

        if len(tempos) < 2:

            return 0

        diferencas = []

        for i in range(1, len(tempos)):

            diferencas.append(
                abs(
                    tempos[i] -
                    tempos[i - 1]
                )
            )

        return round(
            sum(diferencas) /
            len(diferencas),
            2
        )

    except Exception:

        return None


# TESTE
print(get_ping())
print(get_packet_loss())
print(get_jitter())