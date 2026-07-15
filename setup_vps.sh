#!/bin/bash

# --- Real-ESRGAN NVIDIA VPS Auto Setup Script ---
# Ho tro: Ubuntu / Debian

echo "===================================================="
echo "    Bat dau setup Real-ESRGAN API Worker tren VPS"
echo "===================================================="

# 1. Cap nhat he thong & cai dat cac thu vien can thiet
echo -e "\n[1/4] Dang cap nhat he thong va cai dat ffmpeg, python3, tmux..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip ffmpeg tmux git build-essential

# Upgrade pip
python3 -m pip install --upgrade pip --break-system-packages 2>/dev/null || python3 -m pip install --upgrade pip

# Kiem tra neu can them co --break-system-packages do PEP 668
PIP_FLAGS=""
if python3 -m pip install --help | grep -q "break-system-packages"; then
    PIP_FLAGS="--break-system-packages"
fi

# 2. Cai dat PyTorch phu hop voi GPU hoac CPU
echo -e "\n[2/4] Kiem tra GPU va cai dat PyTorch..."
if command -v nvidia-smi &> /dev/null; then
    echo "-> Phat hien co GPU NVIDIA. Cai dat PyTorch ho tro CUDA..."
    python3 -m pip install $PIP_FLAGS torch torchvision --index-url https://download.pytorch.org/whl/cu118
else
    echo "-> Khong tim thay GPU NVIDIA. Cai dat PyTorch phien ban CPU..."
    python3 -m pip install $PIP_FLAGS torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# 3. Cai dat cac thu vien du an
echo -e "\n[3/4] Cai dat cac thu vien phu thuoc..."
python3 -m pip install $PIP_FLAGS -r requirements.txt
python3 -m pip install $PIP_FLAGS fastapi uvicorn python-multipart
python3 setup.py develop --user 2>/dev/null || python3 setup.py develop

# Tai tat ca cac model pre-trained ho tro ve thu muc weights
mkdir -p weights
declare -A models=(
    ["RealESRGAN_x4plus.pth"]="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
    ["RealESRGAN_x4plus_anime_6B.pth"]="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
    ["RealESRGAN_x2plus.pth"]="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"
    ["realesr-animevideov3.pth"]="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth"
    ["realesr-general-x4v3.pth"]="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"
)

for model in "${!models[@]}"; do
    if [ ! -f "weights/$model" ]; then
        echo "-> Tai model $model..."
        wget "${models[$model]}" -P weights/
    fi
done

# 4. Cau hinh Systemd Service chay tu dong
echo -e "\n[4/4] Cau hinh Systemd de chay ngam API..."
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PYTHON_PATH=$(which python3)

cat <<EOF | sudo tee /etc/systemd/system/esrgan.service
[Unit]
Description=Real-ESRGAN API Worker
After=network.target

[Service]
User=$USER
WorkingDirectory=$DIR
ExecStart=$PYTHON_PATH $DIR/worker_api.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable esrgan
sudo systemctl start esrgan

echo "===================================================="
echo "    SETUP HOAN TAT!"
echo "    - API dang chay ngam qua systemd port 8080."
echo "    - Kiem tra trang thai service: sudo systemctl status esrgan"
echo "    - Xem log thoi gian thuc: journalctl -u esrgan -f"
echo "===================================================="
