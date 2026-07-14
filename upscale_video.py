import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import cv2
import os
import subprocess
import tempfile
import shutil
import torch
import numpy as np
from tqdm import tqdm
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from realesrgan.archs.srvgg_arch import SRVGGNetCompact

# ============================================================
#  CAU HINH VIDEO - chinh tai day roi F5
# ============================================================

INPUT_VIDEO   = r"videos\1080x7s.mp4"   # File video dau vao
OUTPUT_VIDEO  = r"results\1080x7s_2K.mp4"  # File video ket qua

# Target resolution (2K doc = 1440x2560, 2K ngang = 2560x1440)
TARGET_W      = 1440
TARGET_H      = 2560

# Model upscale
MODEL_NAME    = "RealESRGAN_x4plus"      # hoac "realesr-animevideov3" cho anime
UPSCALE       = 2                        # 2x: 1072x1920 -> 2144x3840 -> resize 2K
TILE          = 512                      # Tile size de tiet kiem VRAM (0 = khong dung)
TILE_PAD      = 10
GPU_ID        = 0

# FFmpeg encode settings
CRF           = 18       # Chat luong: 0=perfect, 18=visually lossless, 23=default
PRESET        = "slow"   # ultrafast/fast/medium/slow/veryslow

# ============================================================


def build_upsampler():
    name = MODEL_NAME.split(".")[0]

    if name == "RealESRGAN_x4plus":
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
    use_half = torch.cuda.is_available()

    upsampler = RealESRGANer(
        scale=netscale,
        model_path=model_path,
        model=model,
        tile=TILE,
        tile_pad=TILE_PAD,
        pre_pad=0,
        half=use_half,
        gpu_id=GPU_ID,
    )
    return upsampler


def main():
    # --- Kiem tra dau vao ---
    if not os.path.isfile(INPUT_VIDEO):
        print(f"[ERROR] File not found: {INPUT_VIDEO}")
        return

    cap = cv2.VideoCapture(INPUT_VIDEO)
    src_w    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps      = cap.get(cv2.CAP_PROP_FPS)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    print("=" * 60)
    print(f"  Real-ESRGAN Video Upscaler")
    print(f"  Input   : {INPUT_VIDEO}  ({src_w}x{src_h} @ {fps:.2f}fps, {n_frames} frames)")
    print(f"  Target  : {TARGET_W}x{TARGET_H} (2K)")
    print(f"  Model   : {MODEL_NAME}  | Scale: {UPSCALE}x  | Tile: {TILE}")
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"  GPU     : {gpu_name}")
    print("=" * 60)

    # --- Thu muc tam ---
    tmp_dir = os.path.join("results", "_tmp_frames")
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs("results", exist_ok=True)

    # --- Load model ---
    print("\n[1/4] Loading model...")
    upsampler = build_upsampler()
    print("      Done.")

    # --- Xu ly tung frame ---
    print(f"\n[2/4] Upscaling {n_frames} frames...")
    cap = cv2.VideoCapture(INPUT_VIDEO)

    for i in tqdm(range(n_frames), unit="frame", ncols=70):
        ret, frame = cap.read()
        if not ret:
            break

        try:
            output, _ = upsampler.enhance(frame, outscale=UPSCALE)
        except RuntimeError as e:
            print(f"\n[ERROR] Frame {i}: {e}")
            if "out of memory" in str(e).lower():
                print("  -> Reduce TILE size or UPSCALE factor")
            break

        # Resize chinh xac ve TARGET_W x TARGET_H
        if output.shape[1] != TARGET_W or output.shape[0] != TARGET_H:
            output = cv2.resize(output, (TARGET_W, TARGET_H), interpolation=cv2.INTER_LANCZOS4)

        frame_path = os.path.join(tmp_dir, f"frame_{i:06d}.png")
        cv2.imwrite(frame_path, output)

    cap.release()
    print("      All frames processed.")

    # --- Giu lai audio goc ---
    print(f"\n[3/4] Encoding video with ffmpeg...")
    tmp_video = os.path.join("results", "_tmp_noaudio.mp4")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(tmp_dir, "frame_%06d.png"),
        "-c:v", "libx264",
        "-crf", str(CRF),
        "-preset", PRESET,
        "-pix_fmt", "yuv420p",
        tmp_video,
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    # --- Ghep audio tu video goc ---
    print(f"\n[4/4] Merging original audio...")
    ffmpeg_merge = [
        "ffmpeg", "-y",
        "-i", tmp_video,
        "-i", INPUT_VIDEO,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a?",
        "-shortest",
        OUTPUT_VIDEO,
    ]
    subprocess.run(ffmpeg_merge, check=True)

    # --- Don dep ---
    shutil.rmtree(tmp_dir, ignore_errors=True)
    os.remove(tmp_video)

    size_mb = os.path.getsize(OUTPUT_VIDEO) / 1024 / 1024
    print(f"\n{'='*60}")
    print(f"  Done! Output: {os.path.abspath(OUTPUT_VIDEO)}")
    print(f"  Size  : {size_mb:.1f} MB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
