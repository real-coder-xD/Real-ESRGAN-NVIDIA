import requests
import time
import os

# Cau hinh dia chi API VPS cua ban
API_URL = "http://n3.ckey.vn:2172"

# File video can upscale o may local
INPUT_VIDEO_PATH = "videos/720x1080x15s.mp4"
OUTPUT_VIDEO_PATH = "results/upscaled_result.mp4"

def upscale_video_client():
    if not os.path.exists(INPUT_VIDEO_PATH):
        print(f"[ERROR] Khong tim thay file: {INPUT_VIDEO_PATH}")
        return

    # 1. Gui video len API (Upload)
    print(f"\n[1/3] Dang upload video '{INPUT_VIDEO_PATH}' len VPS...")
    
    # Cac tham so nang cap (tuy chon)
    data = {
        "model_name": "RealESRGAN_x4plus",  # Hoac "realesr-animevideov3"
        "upscale": 2,
        "tile": 512
    }
    
    with open(INPUT_VIDEO_PATH, "rb") as f:
        files = {"file": f}
        try:
            response = requests.post(f"{API_URL}/upload", data=data, files=files)
            response.raise_for_status()
            result = response.json()
            task_id = result["task_id"]
            print(f"-> Upload thanh cong! Task ID: {task_id}")
        except Exception as e:
            print(f"[ERROR] Upload that bai: {e}")
            return

    # 2. Polling kiem tra trang thai (Status)
    print("\n[2/3] Dang xu ly video tren VPS...")
    while True:
        try:
            status_resp = requests.get(f"{API_URL}/tasks/{task_id}")
            status_resp.raise_for_status()
            task_info = status_resp.json()
            status = task_info["status"]
            progress = task_info["progress"]
            
            if status == "completed":
                print(f"\r-> Tien trinh: {progress}% - Hoan thanh!")
                break
            elif status == "failed":
                print(f"\n[ERROR] Xu ly video that bai: {task_info.get('error')}")
                return
            else:
                print(f"\r-> Trang thai: {status} | Tien trinh: {progress}%", end="", flush=True)
                
        except Exception as e:
            print(f"\n[WARNING] Loi khi lay trang thai: {e}")
            
        time.sleep(3)  # Kiem tra lai sau moi 3 giay

    # 3. Tai video da upscale ve may local (Download)
    print(f"\n[3/3] Dang tai video da upscale ve '{OUTPUT_VIDEO_PATH}'...")
    os.makedirs(os.path.dirname(OUTPUT_VIDEO_PATH), exist_ok=True)
    
    try:
        with requests.get(f"{API_URL}/tasks/{task_id}/download", stream=True) as r:
            r.raise_for_status()
            with open(OUTPUT_VIDEO_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"-> Tai ve hoan tat! Luu tai: {os.path.abspath(OUTPUT_VIDEO_PATH)}")
    except Exception as e:
        print(f"[ERROR] Tai file that bai: {e}")

if __name__ == "__main__":
    upscale_video_client()
