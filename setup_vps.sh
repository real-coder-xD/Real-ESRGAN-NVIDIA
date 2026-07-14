#!/bin/bash

# --- Real-ESRGAN NVIDIA VPS Auto Setup Script ---
# Ho tro: Ubuntu / Debian

echo "===================================================="
echo "    Bat dau setup Real-ESRGAN API Worker tren VPS"
echo "===================================================="

# 1. Cap nhat he thong & cai dat cac thu vien can thiet
echo -e "\n[1/5] Dang cap nhat he thong va cai dat ffmpeg, python3, tmux..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg tmux git build-essential

# 2. Khoi tao virtual environment (tuy chon, giup sach se he thong)
echo -e "\n[2/5] Khoi tao moi truong ao Python (venv)..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# 3. Cai dat PyTorch phu hop voi GPU hoac CPU
echo -e "\n[3/5] Kiem tra GPU va cai dat PyTorch..."
if command -v nvidia-smi &> /dev/null; then
    echo "-> Phat hien co GPU NVIDIA. Cai dat PyTorch ho tro CUDA..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
else
    echo "-> Khong tim thay GPU NVIDIA. Cai dat PyTorch phien ban CPU..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# 4. Cai dat cac thu vien du an
echo -e "\n[4/5] Cai dat cac thu vien phu thuoc..."
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart
python setup.py develop

# Tai model mac dinh ve thu muc weights neu chua co
mkdir -p weights
if [ ! -f "weights/RealESRGAN_x4plus.pth" ]; then
    echo "-> Tai model RealESRGAN_x4plus.pth..."
    wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -P weights/
fi

# 5. Cau hinh Systemd Service chay tu dong
echo -e "\n[5/5] Cau hinh Systemd de chay ngam API..."
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cat <<EOF | sudo tee /etc/systemd/system/esrgan.service
[Unit]
Description=Real-ESRGAN API Worker
After=network.target

[Service]
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python $DIR/worker_api.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable esrgan
sudo systemctl start esrgan

echo "===================================================="
echo "    SETUP HOAN TAT!"
echo "    - API dang chay ngam qua systemd port 8000."
echo "    - Kiem tra trang thai service: sudo systemctl status esrgan"
echo "    - Xem log thoi gian thuc: journalctl -u esrgan -f"
echo "===================================================="
