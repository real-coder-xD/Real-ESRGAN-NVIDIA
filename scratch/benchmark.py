import os
import subprocess
import time
import torch
import cv2
import numpy as np

# Script test nhanh các thông số để tìm ra cấu hình tốt nhất cho RTX 3060 12GB
# Chạy video test khoảng 100 frames để so sánh tốc độ (FPS) và VRAM tiêu thụ.

INPUT_VIDEO = r"videos\720x15s.mp4"
MODEL_NAME = "realesr-animevideov3"

# Thử nghiệm các giá trị BATCH_SIZE khác nhau
TEST_BATCH_SIZES = [2, 4, 8, 12, 16]
TEST_RESOLUTION = "2K" # Test với 2K cho tải nặng dễ thấy sự khác biệt

def test_config(batch_size):
    from main import build_upsampler, upscale_batch, VIDEO_EXTS
    import queue as Q
    import threading
    
    # Khởi tạo lại upsampler
    upsampler = build_upsampler()
    
    cap = cv2.VideoCapture(INPUT_VIDEO)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    is_portrait = src_h > src_w
    target_w, target_h = (1440, 2560) if is_portrait else (2560, 1440)
    video_scale = target_w / src_w
    
    # Test giới hạn 100 frames để đo tốc độ nhanh chóng
    num_test_frames = 100
    
    # Đọc trước toàn bộ 100 frames vào RAM để loại bỏ ảnh hưởng của tốc độ đọc ổ cứng
    cap = cv2.VideoCapture(INPUT_VIDEO)
    frames_pool = []
    for _ in range(num_test_frames):
        ret, frame = cap.read()
        if not ret:
            break
        frames_pool.append(frame)
    cap.release()
    
    # Đảm bảo đủ frame test
    if len(frames_pool) < num_test_frames:
        num_test_frames = len(frames_pool)

    # Queue giao tiếp
    write_q = Q.Queue(maxsize=128)
    
    # Hàm worker xử lý GPU
    start_time = time.time()
    
    # Đo VRAM bắt đầu
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    vram_start = torch.cuda.memory_allocated() / 1024 / 1024
    
    idx = 0
    while idx < num_test_frames:
        batch = frames_pool[idx:idx+batch_size]
        out_frames = upscale_batch(upsampler, batch, video_scale, (target_h, target_w))
        for f in out_frames:
            write_q.put(f)
        idx += len(batch)
        
    vram_peak = torch.cuda.max_memory_allocated() / 1024 / 1024
    elapsed = time.time() - start_time
    fps_measured = num_test_frames / elapsed
    
    print(f"| Batch Size: {batch_size:2d} | FPS: {fps_measured:6.2f} | Peak VRAM: {vram_peak:7.1f} MB | Time: {elapsed:5.2f}s |")
    return fps_measured, vram_peak

if __name__ == "__main__":
    print("=" * 70)
    print(" BAT DAU BAI KIEM TRA DO HIEU NANG TOI UU CHO RTX 3060 12GB")
    print(f" Thiet bi: {torch.cuda.get_device_name(0)}")
    print(f" Chay thu voi: {TEST_RESOLUTION} (Render tu 720p len 2K), 100 frames.")
    print("=" * 70)

    
    # Cần set môi trường để tránh in log cuda linh tinh
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    
    results = []
    for bs in TEST_BATCH_SIZES:
        try:
            fps, vram = test_config(bs)
            results.append((bs, fps, vram))
        except Exception as e:
            print(f"| Batch Size: {bs:2d} | BI LOI (VRAM Out of Memory hoac loi khac): {e}")
            
    print("=" * 70)
    if results:
        best_bs, best_fps, best_vram = max(results, key=lambda x: x[1])
        print(f" Cau hinh toi uu nhat tim duoc: BATCH_SIZE = {best_bs}")
        print(f" Hieu suat toi da dat: {best_fps:.2f} frames/s (Peak VRAM: {best_vram:.1f} MB)")
    print("=" * 70)

