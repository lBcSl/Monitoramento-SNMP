import psutil

def get_disco():
    disco = psutil.disk_usage('/')

    return {
        "total": round(disco.total / (1024**3), 2),
        "used": round(disco.used / (1024**3), 2),
        "percent": disco.percent
    }