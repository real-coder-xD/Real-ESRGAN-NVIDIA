import os
import cv2
import sys
import torch
import time
import torchvision
import numpy as np
import torch.nn.functional as F

# Hotfix: torchvision 0.17+ removed functional_tensor, patch it for basicsr
try:
    from torchvision.transforms import functional as F
    sys.modules["torchvision.transforms.functional_tensor"] = F
except ImportError:
    pass

import shutil
import subprocess
import queue
import threading
import uuid
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import uvicorn
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from realesrgan.archs.srvgg_arch import SRVGGNetCompact

import sqlite3
from datetime import datetime, timedelta

# Set output encoding to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

app = FastAPI(title="Real-ESRGAN Video Upscale Worker")

UPLOAD_DIR = os.path.join("results", "_uploads")
RESULTS_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# SQLite database setup
DB_PATH = "results/tasks.db"
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT,
            progress INTEGER,
            error TEXT,
            output_path TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def update_task_db(task_id, status, progress, error=None, output_path=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if output_path:
        cursor.execute(
            "INSERT INTO tasks (task_id, status, progress, error, output_path, created_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(task_id) DO UPDATE SET status=?, progress=?, error=?, output_path=?",
            (task_id, status, progress, error, output_path, datetime.utcnow(), status, progress, error, output_path)
        )
    else:
        cursor.execute(
            "INSERT INTO tasks (task_id, status, progress, error, created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(task_id) DO UPDATE SET status=?, progress=?, error=?",
            (task_id, status, progress, error, datetime.utcnow(), status, progress, error)
        )
    conn.commit()
    conn.close()

# In-memory active task database (keeps track of running progress)
tasks = {}
task_queue = queue.Queue()

# Model loader & cache
current_model_name = None
current_upsampler = None
model_lock = threading.Lock()

def get_upsampler(model_name, tile, tile_pad=10, gpu_id=0):
    global current_model_name, current_upsampler
    with model_lock:
        name = model_name.split(".")[0]
        if current_model_name == name and current_upsampler is not None:
            current_upsampler.tile_size = tile
            return current_upsampler
            
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

        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        model_path = os.path.join("weights", f"{name}.pth")
        use_half = torch.cuda.is_available()

        dni_weight = None
        if name == "realesr-general-x4v3":
            wdn_path = os.path.join("weights", "realesr-general-wdn-x4v3.pth")
            if os.path.exists(model_path) and os.path.exists(wdn_path):
                model_path = [model_path, wdn_path]
                dni_weight = [0.2, 0.8]

        current_upsampler = RealESRGANer(
            scale=netscale,
            model_path=model_path,
            dni_weight=dni_weight,
            model=model,
            tile=tile,
            tile_pad=tile_pad,
            pre_pad=0,
            half=use_half,
            gpu_id=gpu_id,
        )
        current_model_name = name
        return current_upsampler

@torch.inference_mode()
def upscale_batch(upsampler, frames, target_size):
    device = upsampler.device
    model = upsampler.model

    tensors = []
    for img in frames:
        t = torch.from_numpy(img).permute(2, 0, 1)
        if device.type == 'cuda':
            t = t.pin_memory()
        tensors.append(t.to(device, non_blocking=True).half().div(255.0))
        
    batch_t = torch.stack(tensors)
    batch_t = batch_t[:, [2, 1, 0], :, :] # BGR -> RGB

    outputs_t = model(batch_t)

    outputs_t = F.interpolate(outputs_t, size=target_size, mode='bilinear', align_corners=False)

    outputs_t = outputs_t[:, [2, 1, 0], :, :].clamp(0, 1).mul(255.0).round().to(torch.uint8)
    outputs = outputs_t.cpu().numpy()

    return [np.transpose(outputs[i], (1, 2, 0)) for i in range(len(frames))]

def worker():
    while True:
        task_id, item = task_queue.get()
        if item is None:
            break
        
        input_path = item["input_path"]
        output_path = item["output_path"]
        model_name = item["model_name"]
        upscale = item["upscale"]
        tile = item["tile"]
        target_w = item["target_w"]
        target_h = item["target_h"]
        is_image = item.get("is_image", False)
        
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 0
        update_task_db(task_id, "processing", 0)
        
        tmp_dir = os.path.join(RESULTS_DIR, f"_tmp_{task_id}")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_video = os.path.join(RESULTS_DIR, f"_tmp_{task_id}_noaudio.mp4")
        
        try:
            upsampler = get_upsampler(model_name, tile)
            
            if is_image:
                img = cv2.imread(input_path)
                if img is None:
                    raise ValueError("Could not read image or image is empty")
                
                output, _ = upsampler.enhance(img, outscale=upscale)
                
                h, w = output.shape[:2]
                final_w, final_h = w, h
                if target_w and target_h:
                    final_w, final_h = target_w, target_h
                elif target_w:
                    final_w = target_w
                    final_h = int(h * (target_w / w))
                elif target_h:
                    final_h = target_h
                    final_w = int(w * (target_h / h))
                
                if final_w != w or final_h != h:
                    output = cv2.resize(output, (final_w, final_h), interpolation=cv2.INTER_LANCZOS4)
                
                cv2.imwrite(output_path, output)
                tasks[task_id]["progress"] = 100
                tasks[task_id]["status"] = "completed"
                update_task_db(task_id, "completed", 100, output_path=output_path)
            else:
                cap = cv2.VideoCapture(input_path)
                src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                if n_frames <= 0:
                    raise ValueError("Could not read video frames or video is empty")
                cap.release()

                if target_w and target_h:
                    target_w_val, target_h_val = target_w, target_h
                elif target_w:
                    target_w_val = target_w
                    target_h_val = int(src_h * (target_w / src_w))
                elif target_h:
                    target_h_val = target_h
                    target_w_val = int(src_w * (target_h / src_h))
                else:
                    target_w_val = int(src_w * upscale)
                    target_h_val = int(src_h * upscale)

                target_w_val = (target_w_val // 2) * 2
                target_h_val = (target_h_val // 2) * 2

                batch_size = 12 if tile == 0 else 1

                if torch.cuda.is_available():
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{target_w_val}x{target_h_val}", "-r", str(fps), "-i", "pipe:0",
                        "-c:v", "h264_nvenc", "-preset", "p7", "-rc", "vbr", "-cq", "16", "-bf", "3",
                        "-pix_fmt", "yuv420p", tmp_video
                    ]
                else:
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{target_w_val}x{target_h_val}", "-r", str(fps), "-i", "pipe:0",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", tmp_video
                    ]

                import queue as Q
                read_q = Q.Queue(maxsize=batch_size * 4)
                write_q = Q.Queue(maxsize=batch_size * 4)
                thread_exc = []

                def reader():
                    try:
                        v = cv2.VideoCapture(input_path)
                        while True:
                            ret, frame = v.read()
                            if not ret:
                                break
                            read_q.put(frame)
                        read_q.put(None)
                        v.release()
                    except Exception as e:
                        thread_exc.append(e)
                        read_q.put(None)

                def worker_thread_fn():
                    try:
                        batch = []
                        while True:
                            frame = read_q.get()
                            if frame is None:
                                if batch:
                                    if tile == 0 and torch.cuda.is_available():
                                        outs = upscale_batch(upsampler, batch, (target_h_val, target_w_val))
                                        for f in outs:
                                            write_q.put(f)
                                    else:
                                        for f in batch:
                                            out, _ = upsampler.enhance(f, outscale=upscale)
                                            if out.shape[1] != target_w_val or out.shape[0] != target_h_val:
                                                out = cv2.resize(out, (target_w_val, target_h_val), interpolation=cv2.INTER_LANCZOS4)
                                            write_q.put(out)
                                write_q.put(None)
                                break
                            
                            batch.append(frame)
                            if len(batch) == batch_size:
                                if tile == 0 and torch.cuda.is_available():
                                    outs = upscale_batch(upsampler, batch, (target_h_val, target_w_val))
                                    for f in outs:
                                        write_q.put(f)
                                else:
                                    for f in batch:
                                        out, _ = upsampler.enhance(f, outscale=upscale)
                                        if out.shape[1] != target_w_val or out.shape[0] != target_h_val:
                                            out = cv2.resize(out, (target_w_val, target_h_val), interpolation=cv2.INTER_LANCZOS4)
                                        write_q.put(out)
                                batch = []
                    except Exception as e:
                        thread_exc.append(e)
                        write_q.put(None)

                ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
                start_time = time.time()
                processed_frames = 0

                def writer():
                    nonlocal processed_frames
                    try:
                        while True:
                            frame = write_q.get()
                            if frame is None:
                                break
                            ffmpeg_proc.stdin.write(frame.tobytes())
                            processed_frames += 1
                            
                            elapsed = time.time() - start_time
                            current_fps = processed_frames / elapsed if elapsed > 0 else 0
                            eta = (n_frames - processed_frames) / current_fps if current_fps > 0 else 0
                            
                            tasks[task_id]["progress"] = min(int(processed_frames / n_frames * 100), 99)
                            tasks[task_id]["speed"] = round(current_fps, 2)
                            tasks[task_id]["eta"] = int(eta)
                            
                            if processed_frames % 5 == 0:
                                update_task_db(task_id, "processing", tasks[task_id]["progress"])
                    except Exception as e:
                        thread_exc.append(e)

                t1 = threading.Thread(target=reader)
                t2 = threading.Thread(target=worker_thread_fn)
                t3 = threading.Thread(target=writer)
                
                for t in [t1, t2, t3]:
                    t.start()
                for t in [t1, t2, t3]:
                    t.join()

                ffmpeg_proc.stdin.close()
                ffmpeg_proc.wait()

                if thread_exc:
                    raise thread_exc[0]
                
                # Merge audio if original video had sound
                ffmpeg_merge = [
                    "ffmpeg", "-y",
                    "-i", tmp_video,
                    "-i", input_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-map", "0:v:0",
                    "-map", "1:a?",
                    "-shortest",
                    output_path,
                ]
                subprocess.run(ffmpeg_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["progress"] = 100
                update_task_db(task_id, "completed", 100, output_path=output_path)
            
        except Exception as e:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)
            update_task_db(task_id, "failed", tasks[task_id]["progress"], error=str(e))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            if os.path.exists(tmp_video):
                os.remove(tmp_video)
            if os.path.exists(input_path):
                os.remove(input_path)
                
        task_queue.task_done()

# Start background thread
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    model_name: str = Form("RealESRGAN_x4plus"),
    upscale: int = Form(2),
    tile: int = Form(512),
    target_w: int = Form(None),
    target_h: int = Form(None)
):
    task_id = str(uuid.uuid4())
    input_filename = f"{task_id}_{file.filename}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    ext = os.path.splitext(file.filename)[1].lower()
    is_image = ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]
    
    output_filename = f"upscaled_{task_id}{ext}" if is_image else f"upscaled_{task_id}.mp4"
    output_path = os.path.join(RESULTS_DIR, output_filename)
    
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "error": None,
        "output_path": output_path,
        "speed": 0,
        "eta": 0
    }
    update_task_db(task_id, "pending", 0)
    
    task_queue.put((task_id, {
        "input_path": input_path,
        "output_path": output_path,
        "model_name": model_name,
        "upscale": upscale,
        "tile": tile,
        "target_w": target_w,
        "target_h": target_h,
        "is_image": is_image
    }))
    
    return {"task_id": task_id, "status": "pending"}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id in tasks:
        task = tasks[task_id]
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "error": task["error"],
            "speed": task.get("speed", 0),
            "eta": task.get("eta", 0)
        }
    
    # Check DB if server restarted
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status, progress, error FROM tasks WHERE task_id=?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "task_id": task_id,
        "status": row[0],
        "progress": row[1],
        "error": row[2],
        "speed": 0,
        "eta": 0
    }

@app.get("/tasks/{task_id}/download")
async def download_result(task_id: str):
    output_path = None
    if task_id in tasks:
        task = tasks[task_id]
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Task is not completed (current status: {task['status']})")
        output_path = task["output_path"]
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, output_path FROM tasks WHERE task_id=?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        if row[0] != "completed":
            raise HTTPException(status_code=400, detail=f"Task is not completed (current status: {row[0]})")
        output_path = row[1]
        
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Upscaled file not found on disk")
        
    ext = os.path.splitext(output_path)[1].lower()
    media_types = {
        ".mp4": "video/mp4",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_types.get(ext, "application/octet-stream")
        
    return FileResponse(
        output_path,
        media_type=media_type,
        filename=os.path.basename(output_path)
    )

@app.get("/stats")
async def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    def count_since(dt):
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", (dt,))
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ? AND status='completed'", (dt,))
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ? AND status='failed'", (dt,))
        failed = cursor.fetchone()[0]
        return {"total": total, "completed": completed, "failed": failed}

    stats = {
        "last_24h": count_since(day_ago),
        "last_7d": count_since(week_ago),
        "last_30d": count_since(month_ago)
    }
    conn.close()
    return stats

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8090))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False, access_log=False)
