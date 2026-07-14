import requests
import time

API_URL = "http://n3.ckey.vn:2172"
INPUT_VIDEO_PATH = "videos/720x1080x15s.mp4"
OUTPUT_VIDEO_PATH = "results/upscaled_result.mp4"

# 1. Upload video
with open(INPUT_VIDEO_PATH, "rb") as f:
    r = requests.post(f"{API_URL}/upload", files={"file": f}, data={"upscale": 2})
    if r.status_code != 200:
        print(f"Server returned status {r.status_code}: {r.text}")
        exit(1)
    try:
        task_id = r.json()["task_id"]
    except Exception as e:
        print(f"Error parsing JSON. Status: {r.status_code}, Response: {r.text}")
        raise e


# 2. Check status
while True:
    try:
        task_info = requests.get(f"{API_URL}/tasks/{task_id}").json()
        status = task_info.get("status")
        progress = task_info.get("progress", 0)
        
        if status == "completed":
            print(f"\r-> Tiến trình: {progress}% - Hoàn thành!")
            break
        elif status == "failed":
            print(f"\n[ERROR] Xử lý thất bại: {task_info.get('error')}")
            exit(1)
        else:
            print(f"\r-> Trạng thái: {status} | Tiến trình: {progress}%", end="", flush=True)
    except Exception as e:
        print(f"\nLỗi khi kết nối: {e}")
        
    time.sleep(3)


# 3. Download result
with requests.get(f"{API_URL}/tasks/{task_id}/download", stream=True) as r:
    with open(OUTPUT_VIDEO_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)