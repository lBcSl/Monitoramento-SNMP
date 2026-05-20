import psutil

def get_cpu():
    return psutil.cpu_percent(interval=(1))


