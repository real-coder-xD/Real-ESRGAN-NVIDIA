import requests
import time
from sshtunnel import SSHTunnelForwarder

# 1. Thiet lap SSH Tunnel tu dong de thong qua firewall cua GPU Cloud
SSH_HOST = "n1.ckey.vn"
SSH_PORT = 2237
SSH_USER = "root"
SSH_PASS = "MD2107fc"
API_INTERNAL_PORT = 8090  # Cong chay thuc te cua API Server trong container

print("[SSH] Dang thiet lap ket noi bao mat den VPS...")
tunnel = SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USER,
    ssh_password=SSH_PASS,
    remote_bind_address=("127.0.0.1", API_INTERNAL_PORT)
)
tunnel.start()

# API se duoc map sang cong local ngau nhien duoc cap bboi sshtunnel
API_URL = f"http://127.0.0.1:{tunnel.local_bind_port}"
print(f"[SSH] Ket noi thanh cong! API noi bo duoc map tai: {API_URL}")

INPUT_VIDEO_PATH = "videos/720x1080x15s.mp4"
OUTPUT_VIDEO_PATH = "results/upscaled_result.mp4"

# 2. Upload video
with open(INPUT_VIDEO_PATH, "rb") as f:
    r = requests.post(
        f"{API_URL}/upload", 
        files={"file": f}, 
        data={
            "upscale": 2, 
            "model_name": "realesr-general-x4v3", 
            "tile": 0
        }
    )
    if r.status_code != 200:
        print(f"Server returned status {r.status_code}: {r.text}")
        tunnel.stop()
        exit(1)
    try:
        task_id = r.json()["task_id"]
    except Exception as e:
        print(f"Error parsing JSON. Status: {r.status_code}, Response: {r.text}")
        tunnel.stop()
        raise e


# 2. Check status
while True:
    try:
        task_info = requests.get(f"{API_URL}/tasks/{task_id}").json()
        status = task_info.get("status")
        progress = task_info.get("progress", 0)
        speed = task_info.get("speed", 0)
        eta = task_info.get("eta", 0)
        
        if status == "completed":
            print(f"\r-> Tien trinh: {progress}% - Hoan thanh!")
            break
        elif status == "failed":
            print(f"\n[ERROR] Xu ly that bai: {task_info.get('error')}")
            tunnel.stop()
            exit(1)
        else:
            print(f"\r-> Tien trinh: {progress}% | Toc do: {speed} fps | ETA: {eta}s   ", end="", flush=True)
    except Exception as e:
        print(f"\nLoi khi ket noi: {e}")
        
    time.sleep(3)


# 3. Download result
with requests.get(f"{API_URL}/tasks/{task_id}/download", stream=True) as r:
    with open(OUTPUT_VIDEO_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

# Dong SSH Tunnel an toan
tunnel.stop()