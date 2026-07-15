import os
import sys
import subprocess
import shutil
import urllib.request

def run_cmd(cmd, shell=False):
    subprocess.run(cmd, shell=shell, check=True)

def main():
    print("====================================================")
    print("    Bat dau setup Real-ESRGAN API Worker va Server")
    print("====================================================")

    # 1. Nang cap pip va kiem tra flags PEP 668
    python_exe = sys.executable
    print("\n[1/4] Dang kiem tra moi truong python...")
    run_cmd([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    
    pip_flags = []
    # Kiem tra neu pip can flag --break-system-packages (PEPs 668)
    try:
        help_out = subprocess.check_output([python_exe, "-m", "pip", "install", "--help"]).decode(errors='ignore')
        if "break-system-packages" in help_out:
            pip_flags.append("--break-system-packages")
    except Exception:
        pass

    # 2. Cai dat PyTorch phu hop voi hardware
    print("\n[2/4] Dang kiem tra GPU va cai dat PyTorch...")
    has_gpu = False
    try:
        import torch
        has_gpu = torch.cuda.is_available()
    except ImportError:
        try:
            smi = subprocess.check_output(["nvidia-smi"])
            has_gpu = True
        except Exception:
            pass

    if has_gpu:
        print("-> Phat hien GPU NVIDIA. Dang cai dat PyTorch ho tro CUDA...")
        run_cmd([python_exe, "-m", "pip", "install"] + pip_flags + ["torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cu118"])
    else:
        print("-> Khong co GPU NVIDIA. Dang cai dat PyTorch CPU...")
        run_cmd([python_exe, "-m", "pip", "install"] + pip_flags + ["torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cpu"])

    # 3. Cai dat cac thu vien du an
    print("\n[3/4] Cai dat cac thu vien phu thuoc...")
    run_cmd([python_exe, "-m", "pip", "install"] + pip_flags + ["-r", "requirements.txt"])
    run_cmd([python_exe, "-m", "pip", "install"] + pip_flags + ["fastapi", "uvicorn", "python-multipart"])
    
    try:
        run_cmd([python_exe, "setup.py", "develop"])
    except Exception:
        run_cmd([python_exe, "setup.py", "develop", "--user"])

    # Tai weights
    print("\n[4/4] Dang tai cac pre-trained weights...")
    os.makedirs("weights", exist_ok=True)
    models = {
        "RealESRGAN_x4plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "RealESRGAN_x4plus_anime_6B.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        "RealESRGAN_x2plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "realesr-animevideov3.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth",
        "realesr-general-x4v3.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"
    }

    for name, url in models.items():
        path = os.path.join("weights", name)
        if not os.path.exists(path):
            print(f"-> Dang tai {name}...")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"Loi khi tai {name}: {e}")

    print("\n====================================================")
    print("    Cai dat thanh cong! Khoi dong API Server...")
    print("====================================================")
    
    # Khoi dong server API
    try:
        run_cmd([python_exe, "worker_api.py"])
    except KeyboardInterrupt:
        print("\nDa dung API Server.")

if __name__ == "__main__":
    main()
