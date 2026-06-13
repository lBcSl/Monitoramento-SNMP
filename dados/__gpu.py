from pynvml import *
import psutil

# INCIAR O NVMLINIT
nvmlInit()

# VALIDAR A CPU DO SITEMA E COLETAR OS DADOS
handle = nvmlDeviceGetHandleByIndex(0)


def get_gpu():

    util = nvmlDeviceGetUtilizationRates(handle)

    memoria = nvmlDeviceGetMemoryInfo(handle)

    return {

        "nome": nvmlDeviceGetName(handle),

        "uso_gpu": util.gpu,

        "uso_memoria_gpu": util.memory,

        "temperatura": nvmlDeviceGetTemperature(
            handle,
            NVML_TEMPERATURE_GPU
        ),

        "memoria_total_gb":
            round(memoria.total / (1024**3), 2),

        "memoria_usada_gb":
            round(memoria.used / (1024**3), 2),

        "memoria_livre_gb":
            round(memoria.free / (1024**3), 2),

        "clock_gpu":
            nvmlDeviceGetClockInfo(
                handle,
                NVML_CLOCK_GRAPHICS
            ),

        "clock_memoria":
            nvmlDeviceGetClockInfo(
                handle,
                NVML_CLOCK_MEM
            ),

        "driver":
            nvmlSystemGetDriverVersion()
    }

# EM TESTES
def get_processos_gpu(): 

    processos = []

    try:

        # PROCESSO PAR VALIDAR USO DA GPU (jogos, navegador, Discord)
        for proc in nvmlDeviceGetGraphicsRunningProcesses(handle):

            try:

                processo = psutil.Process(proc.pid)

                processos.append({

                    "pid": proc.pid,

                    "nome": processo.name(),

                    "memoria_gpu_mb":
                        round(
                            proc.usedGpuMemory / (1024**2),
                            2
                        )

                })

            except Exception:
                pass

    except Exception:
        pass

    return processos

# TESTE
if __name__ == "__main__":

    print("\n GPU ")
    print(get_gpu())

    print("\n PROCESSOS GPU ")
    print(get_processos_gpu())

print(get_gpu())