<p align="center">
  <img src="assets/realesrgan_logo.png" height=120>
</p>

## <div align="center"><b><a href="README.md">English</a> | <a href="README_CN.md">简体中文</a> | <a href="README_VN.md">Tiếng Việt</a></b></div>

<div align="center">

👀[**Demos**](#-demos-videos) **|** 🚩[**Cập nhật**](#-cập-nhật) **|** ⚡[**Cách dùng**](#-hướng-dẫn-chạy-nhanh) **|** 🏰[**Kho mô hình**](docs/model_zoo.md) **|** 🔧[Cài đặt](#-yêu-cầu-và-cài-đặt)  **|** 💻[Huấn luyện](docs/Training.md) **|** ❓[FAQ](docs/FAQ.md) **|** 🎨[Đóng góp](docs/CONTRIBUTING.md)

</div>

🔥 **Mô hình AnimeVideo-v3 (Mô hình video anime nhỏ)**. Vui lòng xem [[*mô hình video anime*](docs/anime_video_model.md)] và [[*so sánh*](docs/anime_comparisons.md)]<br>
🔥 **RealESRGAN_x4plus_anime_6B** cho ảnh anime. Vui lòng xem [[*mô hình anime*](docs/anime_model.md)]

1. :boom: **Cập nhật** demo Replicate online: [![Replicate](https://img.shields.io/static/v1?label=Demo&message=Replicate&color=blue)](https://replicate.com/xinntao/realesrgan)
1. Demo Colab online cho Real-ESRGAN: [![Colab](https://img.shields.io/static/v1?label=Demo&message=Colab&color=orange)](https://colab.research.google.com/drive/1k2Zod6kSHEvraybHl50Lys0LerhyTMCo?usp=sharing) **|** Demo Colab online cho Real-ESRGAN (**video anime**): [![Colab](https://img.shields.io/static/v1?label=Demo&message=Colab&color=orange)](https://colab.research.google.com/drive/1yNl9ORUxxlL4N0keJa2SEPB61imPQd1B?usp=sharing)
1. Các file **chạy độc lập trực tiếp trên Windows/Linux/MacOS hỗ trợ GPU Intel/AMD/Nvidia**. Bạn có thể xem thêm chi tiết tại [đây](#file-chạy-độc-lập-ncnn). Mã nguồn chạy trên ncnn nằm ở [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan)

Real-ESRGAN hướng tới phát triển **Thuật toán Thực tế cho việc Phục hồi Ảnh/Video Tổng quát**.<br>
Chúng tôi mở rộng mô hình ESRGAN mạnh mẽ thành một ứng dụng phục hồi thực tế (Real-ESRGAN), được huấn luyện hoàn toàn bằng dữ liệu tổng hợp.

🌌 Cảm ơn những ý kiến đóng góp và phản hồi quý giá của bạn. Tất cả phản hồi đã được cập nhật tại [feedback.md](docs/feedback.md).

---

Nếu Real-ESRGAN hữu ích với bạn, vui lòng tặng ⭐ cho repo này hoặc giới thiệu cho bạn bè nhé 😊 <br>
Các dự án đề xuất khác:<br>
▶️ [GFPGAN](https://github.com/TencentARC/GFPGAN): Thuật toán thực tế để phục hồi khuôn mặt trong thế giới thực <br>
▶️ [BasicSR](https://github.com/xinntao/BasicSR): Hộp công cụ phục hồi ảnh và video mã nguồn mở<br>
▶️ [facexlib](https://github.com/xinntao/facexlib): Thư viện cung cấp các hàm liên quan đến xử lý khuôn mặt.<br>
▶️ [HandyView](https://github.com/xinntao/HandyView): Trình xem ảnh dựa trên PyQt5 tiện lợi để xem và so sánh ảnh <br>
▶️ [HandyFigure](https://github.com/xinntao/HandyFigure): Mã nguồn mở vẽ hình ảnh cho bài báo khoa học <br>

---

### 📖 Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data

> [[Paper](https://arxiv.org/abs/2107.10833)] &emsp; [[Video YouTube](https://www.youtube.com/watch?v=fxHWoDSSvSc)] &emsp; [[Giải thích trên Bilibili](https://www.bilibili.com/video/BV1H34y1m7sS/)] &emsp; [[Poster](https://xinntao.github.io/projects/RealESRGAN_src/RealESRGAN_poster.pdf)] &emsp; [[Slide PPT](https://docs.google.com/presentation/d/1QtW6Iy8rm8rGLsJ0Ldti6kP-7Qyzy6XL/edit?usp=sharing&ouid=109799856763657548160&rtpof=true&sd=true)]<br>
> [Xintao Wang](https://xinntao.github.io/), Liangbin Xie, [Chao Dong](https://scholar.google.com.hk/citations?user=OSDCB0UAAAAJ), [Ying Shan](https://scholar.google.com/citations?user=4oXBp9UAAAAJ&hl=en) <br>
> [Tencent ARC Lab](https://arc.tencent.com/en/ai-demos/imgRestore); Viện Công nghệ Tiên tiến Thâm Quyến, Học viện Khoa học Trung Quốc

<p align="center">
  <img src="assets/teaser.jpg">
</p>

---

## 🚩 Cập nhật

- ✅ Thêm mô hình **realesr-general-x4v3** - mô hình siêu nhỏ cho các cảnh thông thường. Nó hỗ trợ tùy chọn **-dn** để cân bằng độ nhiễu (tránh kết quả bị quá mịn). **-dn** là viết tắt của denoising strength (cường độ khử nhiễu).
- ✅ Cập nhật mô hình **RealESRGAN AnimeVideo-v3**. Xem chi tiết tại [mô hình video anime](docs/anime_video_model.md) và [so sánh](docs/anime_comparisons.md).
- ✅ Thêm các mô hình nhỏ cho video anime. Chi tiết tại [mô hình video anime](docs/anime_video_model.md).
- ✅ Thêm phiên bản chạy ncnn [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan).
- ✅ Thêm [*RealESRGAN_x4plus_anime_6B.pth*](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth), được tối ưu hóa cho ảnh **anime** với kích thước mô hình nhỏ hơn nhiều. Chi tiết và so sánh với [waifu2x](https://github.com/nihui/waifu2x-ncnn-vulkan) xem tại [**anime_model.md**](docs/anime_model.md).
- ✅ Hỗ trợ finetune trên dữ liệu của riêng bạn hoặc dữ liệu có cặp (*tức là* finetune ESRGAN). Xem hướng dẫn tại [đây](docs/Training.md#Finetune-Real-ESRGAN-on-your-own-dataset).
- ✅ Tích hợp [GFPGAN](https://github.com/TencentARC/GFPGAN) để hỗ trợ **phục hồi khuôn mặt**.
- ✅ Tích hợp vào [Huggingface Spaces](https://huggingface.co/spaces) với [Gradio](https://github.com/gradio-app/gradio). Xem [Demo Web Gradio](https://huggingface.co/spaces/akhaliq/Real-ESRGAN). Cảm ơn [@AK391](https://github.com/AK391).
- ✅ Hỗ trợ tỷ lệ phóng to tùy ý với `--outscale` (chương trình sử dụng thuật toán `LANCZOS4` để resize sau khi mô hình xử lý). Thêm mô hình *RealESRGAN_x2plus.pth*.
- ✅ [Mã nguồn chạy thử (inference code)](inference_realesrgan.py) hỗ trợ: 1) tùy chọn chia ô (**tile**); 2) ảnh có **kênh alpha**; 3) ảnh **grayscale**; 4) ảnh **16-bit**.
- ✅ Mã nguồn huấn luyện đã được phát hành. Hướng dẫn chi tiết tại [Training.md](docs/Training.md).

---

## 👀 Video Demo

#### Bilibili

- [Đại Náo Thiên Cung](https://www.bilibili.com/video/BV1ja41117zb)
- [Anime dance cut](https://www.bilibili.com/video/BV1wY4y1L7hT/)
- [One Piece](https://www.bilibili.com/video/BV1i3411L7Gy/)

#### YouTube

## 🔧 Yêu cầu và Cài đặt

- Python >= 3.7 (Khuyên dùng [Anaconda](https://www.anaconda.com/download/#linux) hoặc [Miniconda](https://docs.conda.io/en/latest/miniconda.html))
- [PyTorch >= 1.7](https://pytorch.org/)

### Cài đặt

1. Clone repo:

    ```bash
    git clone https://github.com/real-coder-xD/Real-ESRGAN-NVIDIA.git
    cd Real-ESRGAN-NVIDIA
    ```

2. Cài đặt các thư viện phụ thuộc:

    ```bash
    # Cài đặt basicsr - https://github.com/xinntao/BasicSR
    # Chúng tôi dùng BasicSR cho cả huấn luyện và suy luận
    pip install basicsr
    # facexlib và gfpgan dùng cho phục hồi khuôn mặt
    pip install facexlib
    pip install gfpgan
    pip install -r requirements.txt
    python setup.py develop
    ```

---

## ⚡ Hướng dẫn chạy nhanh

Thường có 3 cách để chạy Real-ESRGAN.

1. [Chạy online](#chạy-online)
2. [File chạy độc lập (NCNN)](#file-chạy-độc-lập-ncnn)
3. [Script Python](#script-python)

### Chạy online

1. Bạn có thể thử nghiệm trên trang web của chúng tôi: [ARC Demo](https://arc.tencent.com/en/ai-demos/imgRestore) (hiện chỉ hỗ trợ RealESRGAN_x4plus_anime_6B)
2. [Demo Colab](https://colab.research.google.com/drive/1k2Zod6kSHEvraybHl50Lys0LerhyTMCo?usp=sharing) cho Real-ESRGAN **|** [Demo Colab](https://colab.research.google.com/drive/1yNl9ORUxxlL4N0keJa2SEPB61imPQd1B?usp=sharing) cho Real-ESRGAN (**video anime**).

### File chạy độc lập (NCNN)

Bạn có thể tải các file thực thi cho [Windows](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip) / [Linux](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip) / [MacOS](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip) **hỗ trợ GPU Intel/AMD/Nvidia**.

Các file này chạy độc lập và đã tích hợp sẵn mọi mô hình cần thiết, không cần cài đặt môi trường CUDA hay PyTorch.

Ví dụ lệnh chạy trên Windows:

```bash
./realesrgan-ncnn-vulkan.exe -i input.jpg -o output.png -n tên_mô_hình
```

Chúng tôi cung cấp 5 mô hình mặc định:

1. realesrgan-x4plus (mặc định)
2. realesrnet-x4plus
3. realesrgan-x4plus-anime (tối ưu cho ảnh anime, kích thước nhỏ)
4. realesr-animevideov3 (cho video hoạt hình)

Bạn có thể dùng tham số `-n` để chọn mô hình khác, ví dụ: `./realesrgan-ncnn-vulkan.exe -i input.jpg -o output.png -n realesrnet-x4plus`

#### Cách dùng file chạy độc lập

1. Xem thêm chi tiết tại [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan#computer-usages).
2. Lưu ý phiên bản này không hỗ trợ đầy đủ các tính năng (chẳng hạn như `outscale`) giống như script python `inference_realesrgan.py`.

```console
Sử dụng: realesrgan-ncnn-vulkan.exe -i infile -o outfile [tùy chọn]...

  -h                   Hiển thị trợ giúp này
  -i input-path        Đường dẫn ảnh đầu vào (jpg/png/webp) hoặc thư mục
  -o output-path       Đường dẫn ảnh đầu ra (jpg/png/webp) hoặc thư mục
  -s scale             Tỷ lệ phóng to (2, 3, 4. mặc định=4)
  -t tile-size         Kích thước ô chia cắt (>=32/0=tự động, mặc định=0) có thể dùng dạng 0,0,0 cho nhiều GPU
  -m model-path        Thư mục chứa các mô hình đã huấn luyện. mặc định=models
  -n model-name        Tên mô hình (mặc định=realesr-animevideov3, có thể chọn realesr-animevideov3 | realesrgan-x4plus | realesrgan-x4plus-anime | realesrnet-x4plus)
  -g gpu-id            GPU sử dụng (mặc định=auto) có thể dùng dạng 0,1,2 cho nhiều GPU
  -j load:proc:save    Số luồng cho load/proc/save (mặc định=1:2:2) có thể dùng dạng 1:2,2,2:2 cho nhiều GPU
  -x                   Bật chế độ tta
  -f format            Định dạng ảnh đầu ra (jpg/png/webp, mặc định=ext/png)
  -v                   Hiển thị log chi tiết
```

*Lưu ý: Có thể xuất hiện hiện tượng không đồng nhất giữa các ô ghép (và kết quả hơi khác so với bản PyTorch) vì bản thực thi này chia ảnh thành nhiều ô nhỏ để xử lý riêng biệt trước khi ghép lại.*

### Script Python

#### Cách dùng script Python

1. Bạn có thể dùng mô hình X4 cho **kích thước đầu ra tùy ý** bằng tham số `outscale`.

```console
Sử dụng: python inference_realesrgan.py -n RealESRGAN_x4plus -i infile -o outfile [tùy chọn]...

Lệnh thông dụng: python inference_realesrgan.py -n RealESRGAN_x4plus -i infile --outscale 3.5 --face_enhance

  -h                   Hiển thị trợ giúp này
  -i --input           Ảnh đầu vào hoặc thư mục. Mặc định: inputs
  -o --output          Thư mục đầu ra. Mặc định: results
  -n --model_name      Tên mô hình. Mặc định: RealESRGAN_x4plus
  -s, --outscale       Tỷ lệ phóng to cuối cùng. Mặc định: 4
  --suffix             Hậu tố của ảnh phục hồi. Mặc định: out
  -t, --tile           Kích thước ô chia, 0 để không chia ô khi chạy. Mặc định: 0
  --face_enhance       Có sử dụng GFPGAN để phục hồi khuôn mặt hay không. Mặc định: False
  --fp32               Sử dụng độ chính xác fp32 khi chạy. Mặc định: fp16 (half precision).
  --ext                Đuôi mở rộng ảnh đầu ra. Lựa chọn: auto | jpg | png. auto nghĩa là giữ nguyên đuôi gốc. Mặc định: auto
```

#### Phục hồi ảnh thông thường

Tải mô hình pre-trained: [RealESRGAN_x4plus.pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth)

```bash
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -P weights
```

Chạy suy luận:

```bash
python inference_realesrgan.py -n RealESRGAN_x4plus -i inputs --face_enhance
```

Kết quả sẽ được lưu trong thư mục `results`.

#### Phục hồi ảnh anime

<p align="center">
  <img src="https://raw.githubusercontent.com/xinntao/public-figures/master/Real-ESRGAN/cmp_realesrgan_anime_1.png">
</p>

Mô hình pre-trained: [RealESRGAN_x4plus_anime_6B](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth)<br>
Chi tiết và so sánh với [waifu2x](https://github.com/nihui/waifu2x-ncnn-vulkan) xem tại [**anime_model.md**](docs/anime_model.md).

```bash
# Tải mô hình
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth -P weights
# Chạy suy luận
python inference_realesrgan.py -n RealESRGAN_x4plus_anime_6B -i inputs
```

Kết quả sẽ được lưu trong thư mục `results`.

---

## BibTeX

    @InProceedings{wang2021realesrgan,
        author    = {Xintao Wang and Liangbin Xie and Chao Dong and Ying Shan},
        title     = {Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data},
        booktitle = {International Conference on Computer Vision Workshops (ICCVW)},
        date      = {2021}
    }

## 📧 Liên hệ

Nếu có bất kỳ câu hỏi nào, vui lòng gửi email về `xintao.wang@outlook.com` hoặc `xintaowang@tencent.com`.

## 🧩 Các dự án sử dụng Real-ESRGAN

Nếu bạn phát triển hoặc sử dụng Real-ESRGAN trong dự án của mình, rất vui nếu nhận được chia sẻ từ bạn.

- NCNN-Android: [RealSR-NCNN-Android](https://github.com/tumuyan/RealSR-NCNN-Android) tạo bởi [tumuyan](https://github.com/tumuyan)
- VapourSynth: [vs-realesrgan](https://github.com/HolyWu/vs-realesrgan) tạo bởi [HolyWu](https://github.com/HolyWu)
- NCNN: [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan)

&nbsp;&nbsp;&nbsp;&nbsp;**Giao diện đồ họa (GUI)**

- [Waifu2x-Extension-GUI](https://github.com/AaronFeng753/Waifu2x-Extension-GUI) bởi [AaronFeng753](https://github.com/AaronFeng753)
- [Squirrel-RIFE](https://github.com/Justin62628/Squirrel-RIFE) bởi [Justin62628](https://github.com/Justin62628)
- [Real-GUI](https://github.com/scifx/Real-GUI) bởi [scifx](https://github.com/scifx)
- [Real-ESRGAN_GUI](https://github.com/net2cn/Real-ESRGAN_GUI) bởi [net2cn](https://github.com/net2cn)
- [Real-ESRGAN-EGUI](https://github.com/WGzeyu/Real-ESRGAN-EGUI) bởi [WGzeyu](https://github.com/WGzeyu)
- [anime_upscaler](https://github.com/shangar21/anime_upscaler) bởi [shangar21](https://github.com/shangar21)
- [Upscayl](https://github.com/upscayl/upscayl) bởi [Nayam Amarshe](https://github.com/NayamAmarshe) và [TGS963](https://github.com/TGS963)

## 🤗 Lời cảm ơn

Cảm ơn sự đóng góp của tất cả các nhà phát triển.

- [AK391](https://github.com/AK391): Tích hợp RealESRGAN vào [Huggingface Spaces](https://huggingface.co/spaces) với [Gradio](https://github.com/gradio-app/gradio).
- [Asiimoviet](https://github.com/Asiimoviet): Dịch README.md sang tiếng Trung.
- [2ji3150](https://github.com/2ji3150): Cảm ơn những góp ý/phản hồi chi tiết và có giá trị của bạn.
- [Jared-02](https://github.com/Jared-02): Dịch Training.md sang tiếng Trung.
