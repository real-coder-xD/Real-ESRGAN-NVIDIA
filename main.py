import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import cv2
import numpy as np
import glob
import os
import shutil
import subprocess
import torch
import time
import threading, queue as Q

# Hotfix: torchvision 0.17+ removed functional_tensor, patch it for basicsr
try:
    from torchvision.transforms import functional as F_tf
    sys.modules["torchvision.transforms.functional_tensor"] = F_tf
except ImportError:
    pass

from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from realesrgan.archs.srvgg_arch import SRVGGNetCompact
from tqdm import tqdm

# ================================================================
#  CẤU HÌNH TỐI ƯU CHO RTX 4080 SUPER - CHẾ ĐỘ CHI TIẾT THẬT
# ================================================================

INPUT        = r"videos/720x1080x15s.mp4"    # File/thư mục ảnh hoặc video
OUTPUT       = r"results"                    # Thư mục lưu kết quả

# --- 1. CHẾ ĐỘ "THẬT" (QUAN TRỌNG NHẤT) ---
# Dùng "realesr-general-x4v3" để giữ chi tiết da, vải, tóc tốt nhất
MODEL_NAME   = "realesr-general-x4v3" 
# DENOISE_STRENGTH: 0.3 đến 0.5 là THẬT NHẤT. 
# Càng cao càng mịn (nhựa), càng thấp càng giữ hạt/chi tiết gốc.
DENOISE_STRENGTH = 0.2  

# --- 2. CẤU HÌNH VIDEO ---
CRF          = 16          # 16-18 là cực nét cho 2K/4K
PRESET_NVENC = "p7"        # p1-p7: p7 là chất lượng cao nhất cho RTX 4080
USE_NVENC    = False       # Dùng nhân mã hóa phần cứng của GPU (tạm tắt vì container thiếu libnvidia-encode)

# --- 3. CẤU HÌNH ẢNH ---
OUTSCALE     = 4           # Phóng 4 lần
SUFFIX       = "out"       
EXT          = "auto"      
FACE_ENHANCE = False       # True nếu muốn làm nét mặt (cần tải thêm model GFPGAN)

# --- 4. TỐI ƯU PHẦN CỨNG 4080 SUPER (16GB VRAM) ---
BATCH_SIZE     = 12        # Số frame xử lý cùng lúc (4080 cân tốt 12-16)
TILE           = 0         # 0 = Không chia nhỏ (4080 đủ RAM chạy thẳng 4K)
TILE_PAD       = 10
GPU_ID         = 0         
CPU_THREADS    = 16        # Số luồng CPU hỗ trợ I/O
CUDNN_BENCHMARK= True      # Auto-tune CUDA kernel

# ================================================================

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}

def build_upsampler():
    # Tối ưu CUDA cho kiến trúc Ada Lovelace (RTX 40-series)
    if torch.cuda.is_available() and CUDNN_BENCHMARK:
        torch.backends.cudnn.benchmark = True        
        torch.backends.cuda.matmul.allow_tf32 = True 
        torch.backends.cudnn.allow_tf32 = True

    name = MODEL_NAME.split(".")[0]
    
    # Thiết lập cấu trúc mạng dựa trên Model
    if name == "RealESRGAN_x4plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        netscale = 4
    elif name == "RealESRNet_x4plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        netscale = 4
    elif name == "RealESRGAN_x4plus_anime_6B":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
        netscale = 4
    elif name == "RealESRGAN_x2plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        netscale = 2
    elif name == "realesr-animevideov3":
        model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4, act_type="prelu")
        netscale = 4
    elif name == "realesr-general-x4v3":
        model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type="prelu")
        netscale = 4
    else:
        raise ValueError(f"Unknown model: {name}")

    model_path = os.path.join("weights", f"{name}.pth")
    
    # Xử lý DNI (Dynamic Network Interpolation) cho model General để tránh bị "nhựa"
    dni_weight = None
    if name == "realesr-general-x4v3":
        wdn_path = os.path.join("weights", "realesr-general-wdn-x4v3.pth")
        if os.path.exists(model_path) and os.path.exists(wdn_path):
            model_path = [model_path, wdn_path]
            dni_weight = [DENOISE_STRENGTH, 1 - DENOISE_STRENGTH]

    upsampler = RealESRGANer(
        scale=netscale,
        model_path=model_path,
        dni_weight=dni_weight,
        model=model,
        tile=TILE,
        tile_pad=TILE_PAD,
        pre_pad=0,
        half=torch.cuda.is_available(), # Sử dụng FP16 để tăng tốc 2x
        gpu_id=GPU_ID,
    )
        
    return upsampler

def print_header(mode):
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print("=" * 60)
    print(f"  Real-ESRGAN | MODE: {mode} | GPU: {gpu}")
    print(f"  MODEL: {MODEL_NAME} | DENOISE: {DENOISE_STRENGTH}")
    print(f"  INPUT: {INPUT}")
    print("=" * 60 + "\n")

# ----------------------------------------------------------------
#  PHẦN XỬ LÝ ẢNH (GIỮ NGUYÊN 100%)
# ----------------------------------------------------------------
def run_images(upsampler):
    start_time = time.time()
    face_enh = None
    if FACE_ENHANCE:
        from gfpgan import GFPGANer
        face_enh = GFPGANer(
            model_path="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth",
            upscale=OUTSCALE, arch="clean", channel_multiplier=2, bg_upsampler=upsampler)

    os.makedirs(OUTPUT, exist_ok=True)
    fixed_input = INPUT.replace('\\', '/')

    if os.path.isfile(fixed_input):
        paths = [fixed_input]
    else:
        paths = [p for p in sorted(glob.glob(os.path.join(fixed_input, "*")))
                 if os.path.splitext(p)[1].lower() in IMAGE_EXTS]

    if not paths:
        print(f"[!] Không tìm thấy ảnh trong: {fixed_input}")
        return

    print(f"Tìm thấy {len(paths)} ảnh...\n")
    for idx, path in enumerate(paths):
        imgname, ext = os.path.splitext(os.path.basename(path))
        print(f"[{idx+1}/{len(paths)}] {imgname}{ext}", end=" -> ", flush=True)

        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print("Lỗi đọc file")
            continue

        try:
            if FACE_ENHANCE and face_enh:
                _, _, output = face_enh.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
            else:
                output, _ = upsampler.enhance(img, outscale=OUTSCALE)
        except Exception as e:
            print(f"Lỗi: {e}")
            continue

        save_ext = ext[1:] if EXT == "auto" else EXT
        save_name = f"{imgname}_{SUFFIX}.{save_ext}" if SUFFIX else f"{imgname}.{save_ext}"
        cv2.imwrite(os.path.join(OUTPUT, save_name), output)
        print(f"OK ({output.shape[1]}x{output.shape[0]})")

    print(f"\nHoàn thành trong {time.time()-start_time:.2f}s")

# ----------------------------------------------------------------
#  BATCH INFERENCE (Tối ưu Tensor Core cho 4080)
# ----------------------------------------------------------------
# ----------------------------------------------------------------
#  BATCH INFERENCE (Tối ưu Tensor Core & Pin Memory cho 4080)
# ----------------------------------------------------------------
@torch.inference_mode()
def upscale_batch(upsampler, frames, target_size):
    device = upsampler.device
    model = upsampler.model

    # Đưa tensor lên pinned memory trước khi nạp non-blocking lên GPU để tối ưu băng thông PCIe
    tensors = []
    for img in frames:
        t = torch.from_numpy(img).permute(2, 0, 1)
        if device.type == 'cuda':
            t = t.pin_memory()
        tensors.append(t.to(device, non_blocking=True).half().div(255.0))
        
    batch_t = torch.stack(tensors)
    batch_t = batch_t[:, [2, 1, 0], :, :] # BGR -> RGB

    # Chạy model
    outputs_t = model(batch_t)

    # Resize trực tiếp trên GPU bằng CUDA
    import torch.nn.functional as F
    outputs_t = F.interpolate(outputs_t, size=target_size, mode='bilinear', align_corners=False)

    # Chuyển đổi ngược về BGR uint8 trước khi kéo về CPU
    outputs_t = outputs_t[:, [2, 1, 0], :, :].clamp(0, 1).mul(255.0).round().to(torch.uint8)
    outputs = outputs_t.cpu().numpy()

    return [np.transpose(outputs[i], (1, 2, 0)) for i in range(len(frames))]

# ----------------------------------------------------------------
#  PHẦN XỬ LÝ VIDEO (3-Thread Pipeline)
# ----------------------------------------------------------------
def run_video(upsampler):
    start_time = time.time()
    fixed_input = INPUT.replace('\\', '/')
    
    cap = cv2.VideoCapture(fixed_input)
    if not cap.isOpened():
        print(f"\n[LỖI] Không thể mở video: {fixed_input}")
        return

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps   = cap.get(cv2.CAP_PROP_FPS)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # Xác định độ phân giải bảo toàn tỷ lệ khung hình (Aspect Ratio) gốc
    if RESOLUTION == "4K":
        max_edge = 3840
    elif RESOLUTION == "2K":
        max_edge = 2560
    else:
        max_edge = 1920

    if src_h > src_w: # Video dọc (Portrait)
        target_h = max_edge
        target_w = int(src_w * (target_h / src_h))
        # Đảm bảo chia hết cho 2 để encoder H.264/H.265 không lỗi
        target_w = (target_w // 2) * 2
    else: # Video ngang (Landscape)
        target_w = max_edge
        target_h = int(src_h * (target_w / src_w))
        # Đảm bảo chia hết cho 2 để encoder H.264/H.265 không lỗi
        target_h = (target_h // 2) * 2

    basename = os.path.splitext(os.path.basename(fixed_input))[0]
    out_path = os.path.join(OUTPUT, f"{basename}_{RESOLUTION}_Real.mp4").replace('\\', '/')
    os.makedirs(OUTPUT, exist_ok=True)

    print(f"  XỬ LÝ: {src_w}x{src_h} -> {target_w}x{target_h} ({RESOLUTION})")
    print(f"  THIẾT LẬP: Batch Size={BATCH_SIZE}, Denoise={DENOISE_STRENGTH}, NVENC={PRESET_NVENC}\n")

    # FFmpeg Command
    if USE_NVENC:
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
            "-s", f"{target_w}x{target_h}", "-r", str(fps), "-i", "pipe:0", "-i", fixed_input,
            "-c:v", "h264_nvenc", "-preset", PRESET_NVENC, "-rc", "vbr", "-cq", str(CRF), "-bf", "3",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a?", "-shortest", out_path,
        ]
    else:
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
            "-s", f"{target_w}x{target_h}", "-r", str(fps), "-i", "pipe:0", "-i", fixed_input,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a?", "-shortest", out_path,
        ]
    # bufsize=10**8 (~100MB) giúp tăng tốc trao đổi dữ liệu qua pipe, triệt tiêu nghẽn I/O
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)

    read_q = Q.Queue(maxsize=BATCH_SIZE * 4)
    write_q = Q.Queue(maxsize=BATCH_SIZE * 4)

    def reader():
        v = cv2.VideoCapture(fixed_input)
        while True:
            ret, frame = v.read()
            if not ret: break
            read_q.put(frame)
        read_q.put(None)
        v.release()

    def worker():
        batch = []
        while True:
            frame = read_q.get()
            if frame is None:
                if batch:
                    outs = upscale_batch(upsampler, batch, (target_h, target_w))
                    for f in outs: write_q.put(f)
                write_q.put(None)
                break
            batch.append(frame)
            if len(batch) == BATCH_SIZE:
                outs = upscale_batch(upsampler, batch, (target_h, target_w))
                for f in outs: write_q.put(f)
                batch = []

    pbar = tqdm(total=n_frames, unit="frame", ncols=80)
    def writer():
        while True:
            frame = write_q.get()
            if frame is None: break
            ffmpeg_proc.stdin.write(frame.tobytes())
            pbar.update(1)

    t1 = threading.Thread(target=reader)
    t2 = threading.Thread(target=worker)
    t3 = threading.Thread(target=writer)
    for t in [t1, t2, t3]: t.start()
    for t in [t1, t2, t3]: t.join()

    pbar.close()
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    
    elapsed = time.time() - start_time
    print(f"\nDone! Video lưu tại: {out_path}")
    print(f"Tổng thời gian xử lý: {elapsed:.2f}s (Tốc độ trung bình: {n_frames/elapsed:.2f} FPS)")

# ----------------------------------------------------------------
#  ĐIỂM CHẠY CHÍNH
# ----------------------------------------------------------------
RESOLUTION = "1K"
def main():
    global RESOLUTION
    fixed_input = INPUT.replace('\\', '/')
    if not os.path.exists(fixed_input):
        print(f"Lỗi: Không tìm thấy file {fixed_input}")
        return

    ext = os.path.splitext(fixed_input)[1].lower()
    if ext in VIDEO_EXTS:
        print("=" * 60)
        print(" CHỌN ĐỘ PHÂN GIẢI RENDER VIDEO (RTX 4080 SUPER):")
        print(" [1] 1080p | [2] 2K (1440p) | [3] 4K (2160p)")
        c = input("Lựa chọn (mặc định 2): ")
        if c == "1": RESOLUTION = "1K"
        elif c == "3": RESOLUTION = "4K"
        else: RESOLUTION = "2K"

        print_header("VIDEO")
        upsampler = build_upsampler()
        run_video(upsampler)
    else:
        print_header("IMAGE")
        upsampler = build_upsampler()
        run_images(upsampler)

if __name__ == "__main__":
    main()
