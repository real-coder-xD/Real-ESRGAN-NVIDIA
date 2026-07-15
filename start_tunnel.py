import time
import sys
from sshtunnel import SSHTunnelForwarder

SSH_HOST = "n1.ckey.vn"
SSH_PORT = 2237
SSH_USER = "root"
SSH_PASS = "MD2107fc"
API_INTERNAL_PORT = 8090
LOCAL_PORT = 8090

print("[SSH] Dang thiet lap ket noi bao mat den VPS...")
try:
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASS,
        remote_bind_address=("127.0.0.1", API_INTERNAL_PORT),
        local_bind_address=("127.0.0.1", LOCAL_PORT)
    )
    tunnel.start()
    print(f"[SSH] Ket noi thanh cong! API da duoc map co dinh tai: http://127.0.0.1:{LOCAL_PORT}")
    print("=> Ban co the giu cua so nay de duy tri session, khong can dang nhap lai khi chay client.")
    print("Nhan Ctrl+C de dong ket noi.")
    
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[SSH] Dang dong ket noi...")
    tunnel.stop()
except Exception as e:
    print(f"[ERROR] Khong the thiet lap Tunnel: {e}")
