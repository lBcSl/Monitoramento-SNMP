import psutil

def get_processos():
    processos = []
    for proc in psutil.process_iter():

        try:

            processos.append({
                "pid": proc.pid,
                "nome": proc.name(),
                "cpu": proc.cpu_percent(),
                "memoria_mb":
                    round(
                        proc.memory_info().rss /
                        (1024 * 1024),
                        2
                    ),
                "threads": proc.num_threads(),
                "status": proc.status()
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            pass

    processos.sort(
        key=lambda x: x["memoria_mb"],
        reverse=True
    )

    return processos[:10]