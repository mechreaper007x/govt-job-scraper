import socket

domains = [
    "arvalli.nic.in",
    "nabarangpur.odisha.gov.in",
    "peren-district.nic.in",
    "sundargarh.odisha.gov.in",
    "punjabroadways.gov.in",
    "punjabroadways.in"
]

for d in domains:
    try:
        ip = socket.gethostbyname(d)
        print(f"{d:<30} -> {ip}")
    except Exception as e:
        print(f"{d:<30} -> Fail: {e}")
