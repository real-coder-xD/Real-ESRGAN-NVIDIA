import os
import sys
import subprocess
import shutil
import urllib.request

def run_cmd(cmd, shell=False):
    subprocess.run(cmd, shell=shell, check=True)

def install_system_dependencies():
    # Neu la Linux thi tu dong kiem tra va cai dat goi he thong cho OpenCV neu thieu
    if sys.platform.startswith("linux"):
        print("\n-> Dang kiem tra va cai dat cac thu vien do hoa hệ thong cho OpenCV...")
        try:
            # Thu kiem tra xem co quyen root hoac co apt-get khong
            if os.getuid() == 0:
                subprocess.run(["apt-get", "update"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["apt-get", "install", "-y", "libgl1-mesa-glx", "libglib2.0-0", "libxcb1"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["sudo", "apt-get", "update"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["sudo", "apt-get", "install", "-y", "libgl1-mesa-glx", "libglib2.0-0", "libxcb1"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def main():
    print("====================================================")
    print("    Bat dau setup Real-ESRGAN API Worker va Server")
    print("====================================================")
    install_system_dependencies()

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
    
    # Tu dong giai phong cong 8080 neu bi chiem dung truoc khi chay
    if sys.platform.startswith("linux"):
        print("-> Dang kiem tra va giai phong cong 8080...")
        try:
            import signal
            # Quet qua /proc de tim PID chiem cong 8080
            target_port_hex = "1F90" # 8080 in hex
            pids_to_kill = set()
            
            # Buoc 1: Xem tat ca socket kết nối o cong 8080
            inodes = []
            for path in ["/proc/net/tcp", "/proc/net/tcp6"]:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        lines = f.readlines()[1:]
                        for line in lines:
                            parts = line.strip().split()
                            if len(parts) >= 10:
                                local_address = parts[1]
                                local_port = local_address.split(":")[-1]
                                if local_port.upper() == target_port_hex:
                                    inodes.append(parts[9])
                                    
            # Buoc 2: Tim PID so khop voi inode
            if inodes:
                for pid in os.listdir("/proc"):
                    if pid.isdigit():
                        fd_dir = os.path.join("/proc", pid, "fd")
                        if os.path.exists(fd_dir):
                            try:
                                for fd in os.listdir(fd_dir):
                                    link = os.readlink(os.path.join(fd_dir, fd))
                                    for inode in inodes:
                                        if inode in link:
                                            pids_to_kill.add(int(pid))
                            except Exception:
                                pass
                                
            # Kill processes
            current_pid = os.getpid()
            for pid in pids_to_kill:
                if pid != current_pid:
                    try:
                        # Kill ca process group de diet sach con chau cua no
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGKILL)
                        print(f"-> Da tat nhom tien trinh chiem cong: PGID {pgid}")
                    except Exception:
                        try:
                            os.kill(pid, signal.SIGKILL)
                            print(f"-> Da tat tien trinh cu dang chiem cong: PID {pid}")
                        except Exception:
                            pass
                        
            # Phòng hờ quet them tat ca tien trinh python dang chay worker_api.py hoac uvicorn bang lenh ps
            try:
                # Quét mọi tiến trình python liên quan
                ps_out = subprocess.check_output(["ps", "-ef"]).decode()
                for line in ps_out.splitlines():
                    if "worker_api.py" in line or "uvicorn" in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            pid = int(parts[1])
                            if pid != current_pid:
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                except Exception:
                                    pass
            except Exception:
                pass
                
            # Đợi 2 giây để hệ thống giải phóng cổng hẳn
            import time
            time.sleep(2.0)
        except Exception as e:
            print(f"Loi khi giai phong cong: {e}")

    # Khoi dong server API
    try:
        run_cmd([python_exe, "worker_api.py"])
    except KeyboardInterrupt:
        print("\nDa dung API Server.")

if __name__ == "__main__":
    main()
