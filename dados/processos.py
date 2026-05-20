import psutil

def get_processos():
    processos = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):

        try:

            info = proc.info

            processos.append({
                "pid": info['pid'],
                "nome": info['name'],
                "cpu": info['cpu_percent'],
                "memoria": round(info['memory_percent'], 2)
            })

        except:
            pass

    processos = sorted(processos, key=lambda x: x['cpu'], reverse=True)

    return processos[:5]