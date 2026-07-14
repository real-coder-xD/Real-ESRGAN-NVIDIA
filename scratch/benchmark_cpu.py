import os
import time
import subprocess
import torch
import cv2
import numpy as np
import psutil

# Script benchmark đo hiệu năng tác động của các cài đặt liên quan CPU & RAM (Encode, Luồng) 
# trên cấu hình i5-12400F (12 threads) & 16GB RAM của bạn.

INPUT_VIDEO = r"videos\720x15s.mp4"
MODEL_NAME = "realesr-animevideov3"
NUM_FRAMES = 100

def run_benchmark(use_nvenc, cpu_threads, queue_size):
    from main import build_upsampler, upscale_batch
    import queue as Q
    import threading

    # Khởi tạo GPU worker và cấu hình
    upsampler = build_upsampler()
    
    cap = cv2.VideoCapture(INPUT_VIDEO)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    is_portrait = src_h > src_w
    target_w, target_h = (1440, 2560) if is_portrait else (2560, 1440)
    video_scale = target_w / src_w
    out_path = r"results\test_perf.mp4"
    
    if use_nvenc:
        video_codec = ["h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "18", "-b:v", "0"]
    else:
        video_codec = ["libx264", "-crf", "18", "-preset", "fast", "-threads", str(cpu_threads)]
        
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{target_w}x{target_h}", "-r", str(fps), "-i", "pipe:0",
        "-c:v", *video_codec, "-pix_fmt", "yuv420p", out_path
    ]
    
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    read_q = Q.Queue(maxsize=queue_size)
    write_q = Q.Queue(maxsize=queue_size)
    
    # Đo CPU & RAM sử dụng lúc bắt đầu
    process = psutil.Process(os.getpid())
    ram_start = process.memory_info().rss / 1024 / 1024
    
    cpu_usages = []
    ram_usages = []
    
    def video_reader():
        cap = cv2.VideoCapture(INPUT_VIDEO)
        for _ in range(NUM_FRAMES):
            ret, frame = cap.read()
            if not ret:
                break
            read_q.put(frame)
        cap.release()
        read_q.put(None)
        
    def gpu_worker():
        batch = []
        while True:
            frame = read_q.get()
            if frame is None:
                if batch:
                    out_frames = upscale_batch(upsampler, batch, video_scale, (target_h, target_w))
                    for f in out_frames:
                        write_q.put(f)
                write_q.put(None)
                read_q.task_done()
                break
            batch.append(frame)
            if len(batch) == 4: # BATCH_SIZE cố định tối ưu nhất đã test ở trước
                out_frames = upscale_batch(upsampler, batch, video_scale, (target_h, target_w))
                for f in out_frames:
                    write_q.put(f)
                batch = []
            read_q.task_done()
            
    def ffmpeg_writer():
        while True:
            frame = write_q.get()
            if frame is None:
                write_q.task_done()
                break
            ffmpeg_proc.stdin.write(frame.tobytes())
            write_q.task_done()
            
    t_reader = threading.Thread(target=video_reader, daemon=True)
    t_worker = threading.Thread(target=gpu_worker, daemon=True)
    t_writer = threading.Thread(target=ffmpeg_writer, daemon=True)
    
    start_time = time.time()
    
    t_reader.start()
    t_worker.start()
    t_writer.start()
    
    # Lấy mẫu CPU & RAM trong quá trình chạy
    while t_writer.is_alive():
        cpu_usages.append(psutil.cpu_percent(interval=0.1))
        ram_usages.append(process.memory_info().rss / 1024 / 1024)
        time.sleep(0.2)
        
    t_reader.join()
    t_worker.join()
    t_writer.join()
    
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    
    elapsed = time.time() - start_time
    fps = NUM_FRAMES / elapsed
    
    avg_cpu = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0
    max_ram = max(ram_usages) if ram_usages else ram_start
    
    # Xóa file test
    if os.path.exists(out_path):
        os.remove(out_path)
        
    return fps, avg_cpu, max_ram

if __name__ == "__main__":
    print("=" * 80)
    print(" BAT DAU BENCHMARK CPU & RAM (KHAO SAT ENCODE & QUEUE SIZE)")
    print("=" * 80)
    
    # Test cases: (Tên test, Dùng NVENC (GPU Encode), Số threads CPU nếu CPU encode, Cỡ Queue)
    test_cases = [
        ("1. GPU Encode (NVENC) + Queue 16", True, 0, 16),
        ("2. GPU Encode (NVENC) + Queue 64", True, 0, 64),
        ("3. CPU Encode (libx264 4 thds) + Queue 64", False, 4, 64),
        ("4. CPU Encode (libx264 12 thds) + Queue 64", False, 12, 64),
    ]
    
    for name, use_nvenc, thds, q_size in test_cases:
        try:
            fps, cpu, ram = run_benchmark(use_nvenc, thds, q_size)
            print(f"| {name:<40} | FPS: {fps:5.2f} | CPU Avg: {cpu:5.1f}% | RAM Peak: {ram:6.1f} MB |")
        except Exception as e:
            print(f"| Lỗi test {name}: {e}")
            
    print("=" * 80)
