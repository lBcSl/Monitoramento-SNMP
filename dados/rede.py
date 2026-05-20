import psutil

def get_rede():
    rede = psutil.net_io_counters()

    return {
        "bytes_sent": rede.bytes_sent,
        "bytes_recv": rede.bytes_recv
    }