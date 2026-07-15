import requests
import time
import socket
import cv2
from sshtunnel import SSHTunnelForwarder

# Cau hinh SSH
SSH_HOST = "n1.ckey.vn"
SSH_PORT = 2237
SSH_USER = "root"
SSH_PASS = "MD2107fc"
API_INTERNAL_PORT = 8090
LOCAL_PORT = 8090

INPUT_VIDEO_PATH = "videos/720x1080x15s.mp4"
OUTPUT_VIDEO_PATH = "results/upscaled_result.mp4"

# 1. Hien thi menu chon do phan giai giong main.py
print("============================================================")
print(" CHỌN ĐỘ PHÂN GIẢI RENDER VIDEO QUA API (RTX 4080 SUPER):")
print(" [1] 1080p | [2] 2K (1440p) | [3] 4K (2160p)")
choice = input("Lựa chọn (mặc định 2): ").strip()
if choice == "1":
    resolution = "1080p"
    max_edge = 1920
elif choice == "3":
    resolution = "4K"
    max_edge = 3840
else:
    resolution = "2K"
    max_edge = 2560

# Doc file video local de lay thong tin va tinh target size
cap = cv2.VideoCapture(INPUT_VIDEO_PATH)
if not cap.isOpened():
    print(f"[ERROR] Khong the mo file video: {INPUT_VIDEO_PATH}")
    exit(1)
src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

if src_h > src_w:  # Video doc
    target_h = max_edge
    target_w = int(src_w * (target_h / src_h))
    target_w = (target_w // 2) * 2
else:  # Video ngang
    target_w = max_edge
    target_h = int(src_h * (target_w / src_w))
    target_h = (target_h // 2) * 2

print(f" -> Kich thuoc render: {src_w}x{src_h} -> {target_w}x{target_h} ({resolution})")
print("============================================================")

# Ham kiem tra xem port local da duoc mo san (tu start_tunnel.py) hay chua
def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

tunnel = None
if is_port_open(LOCAL_PORT):
    API_URL = f"http://127.0.0.1:{LOCAL_PORT}"
    print(f"[SSH] Phat hien Tunnel dang chay san. Su dung: {API_URL}")
else:
    print("[SSH] Tunnel chua mo. Dang tu dong khoi tao Tunnel tam thoi...")
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASS,
        remote_bind_address=("127.0.0.1", API_INTERNAL_PORT)
    )
    tunnel.start()
    API_URL = f"http://127.0.0.1:{tunnel.local_bind_port}"
    print(f"[SSH] Tunnel tam thoi khoi tao tai: {API_URL}")

# Lam viec theo Session de giu ket noi TCP va toi uu toc do request
with requests.Session() as session:
    # 1. Upload video
    print(f"\n[1/3] Dang upload video len server...")
    with open(INPUT_VIDEO_PATH, "rb") as f:
        r = session.post(
            f"{API_URL}/upload", 
            files={"file": f}, 
            data={
                "upscale": 2, 
                "model_name": "realesr-general-x4v3", 
                "tile": 0,
                "denoise_strength": 0.35,
                "target_w": target_w,
                "target_h": target_h
            }
        )
        if r.status_code != 200:
            print(f"Server returned status {r.status_code}: {r.text}")
            if tunnel: tunnel.stop()
            exit(1)
        try:
            task_id = r.json()["task_id"]
        except Exception as e:
            print(f"Error parsing JSON. Status: {r.status_code}, Response: {r.text}")
            if tunnel: tunnel.stop()
            raise e

    # 2. Check status
    print("[2/3] Dang xu ly video...")
    start_time = time.time()
    while True:
        try:
            task_info = session.get(f"{API_URL}/tasks/{task_id}").json()
            status = task_info.get("status")
            progress = task_info.get("progress", 0)
            speed = task_info.get("speed", 0)
            eta = task_info.get("eta", 0)
            
            if status == "completed":
                elapsed_time = time.time() - start_time
                print(f"\r-> Tien trinh: {progress}% - Hoan thanh! (Tong thoi gian: {elapsed_time:.2f}s)")
                break
            elif status == "failed":
                print(f"\n[ERROR] Xu ly that bai: {task_info.get('error')}")
                if tunnel: tunnel.stop()
                exit(1)
            else:
                print(f"\r-> Tien trinh: {progress}% | Toc do: {speed} fps | ETA: {eta}s   ", end="", flush=True)
        except Exception as e:
            print(f"\nLoi khi ket noi: {e}")
            
        time.sleep(1)

    # 3. Download result
    print(f"\n[3/3] Dang tai video ket qua ve...")
    with session.get(f"{API_URL}/tasks/{task_id}/download", stream=True) as r:
        with open(OUTPUT_VIDEO_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"-> Hoan thanh! Video da duoc luu tai: {OUTPUT_VIDEO_PATH}")

# Dong SSH Tunnel neu duoc khoi tao tam thoi trong file nay
if tunnel:
    tunnel.stop()