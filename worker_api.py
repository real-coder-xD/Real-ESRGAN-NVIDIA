import os
import cv2
import torch
import shutil
import subprocess
import queue
import threading
import uuid
import sys
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import uvicorn
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from realesrgan.archs.srvgg_arch import SRVGGNetCompact

# Set output encoding to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

app = FastAPI(title="Real-ESRGAN Video Upscale Worker")

UPLOAD_DIR = os.path.join("results", "_uploads")
RESULTS_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# In-memory task database
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

        model_path = os.path.join("weights", f"{name}.pth")
        use_half = torch.cuda.is_available()

        current_upsampler = RealESRGANer(
            scale=netscale,
            model_path=model_path,
            model=model,
            tile=tile,
            tile_pad=tile_pad,
            pre_pad=0,
            half=use_half,
            gpu_id=gpu_id,
        )
        current_model_name = name
        return current_upsampler

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
        
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 0
        
        tmp_dir = os.path.join(RESULTS_DIR, f"_tmp_{task_id}")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_video = os.path.join(RESULTS_DIR, f"_tmp_{task_id}_noaudio.mp4")
        
        try:
            cap = cv2.VideoCapture(input_path)
            src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if n_frames <= 0:
                raise ValueError("Could not read video frames or video is empty")
                
            upsampler = get_upsampler(model_name, tile)
            
            for i in range(n_frames):
                ret, frame = cap.read()
                if not ret:
                    break
                
                output, _ = upsampler.enhance(frame, outscale=upscale)
                
                if target_w and target_h:
                    if output.shape[1] != target_w or output.shape[0] != target_h:
                        output = cv2.resize(output, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                
                frame_path = os.path.join(tmp_dir, f"frame_{i:06d}.png")
                cv2.imwrite(frame_path, output)
                
                tasks[task_id]["progress"] = int((i + 1) / n_frames * 100)
            
            cap.release()
            
            # Encode video with ffmpeg
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", os.path.join(tmp_dir, "frame_%06d.png"),
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "slow",
                "-pix_fmt", "yuv420p",
                tmp_video,
            ]
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
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
            
        except Exception as e:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)
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
async def upload_video(
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
        
    output_filename = f"upscaled_{task_id}.mp4"
    output_path = os.path.join(RESULTS_DIR, output_filename)
    
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "error": None,
        "output_path": output_path
    }
    
    task_queue.put((task_id, {
        "input_path": input_path,
        "output_path": output_path,
        "model_name": model_name,
        "upscale": upscale,
        "tile": tile,
        "target_w": target_w,
        "target_h": target_h
    }))
    
    return {"task_id": task_id, "status": "pending"}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "error": task["error"]
    }

@app.get("/tasks/{task_id}/download")
async def download_result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed (current status: {task['status']})")
        
    if not os.path.exists(task["output_path"]):
        raise HTTPException(status_code=404, detail="Upscaled file not found on disk")
        
    return FileResponse(
        task["output_path"],
        media_type="video/mp4",
        filename=os.path.basename(task["output_path"])
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
