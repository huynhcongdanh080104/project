from time import time

requests = {}

def check_rate_limit(ip: str):
    now = time()

    if ip not in requests:
        requests[ip] = {
            "count": 1,
            "window_start": now
        }
        return True
    
    data = requests[ip]

    if now - data["window_start"] >= 60:
        requests[ip] = {
            "count": 1,
            "window_start": now
        }
        return True

    data["count"] += 1

    if data["count"] > 5:
        return False

    return True