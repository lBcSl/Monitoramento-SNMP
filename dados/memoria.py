import psutil

def get_memoria():

    memoria = psutil.virtual_memory()

    return {
        "total": round(memoria.total / (1024**3), 2),
        "used": round(memoria.used / (1024**3), 2),
        "percent": memoria.percent
    }