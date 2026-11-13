FROM python:3.12-slim

# OpenCV 실행에 필요한 시스템 라이브러리
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Python 패키지 관리자
RUN pip install --no-cache-dir uv==0.13.8

# CPU 전용 PyTorch
RUN uv pip install --system \
    torch==2.15.0+cpu \
    torchvision==0.29.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# YOLO
RUN uv pip install --system ultralytics==8.4.211

WORKDIR /workspace

CMD ["bash"]
