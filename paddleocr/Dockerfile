# Dockerfile - PaddleOCR Service (PaddleOCR-VL-1.5 with Bengali support)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    libxrender1 \
    libfontconfig1 \
    libx11-6 \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Install uv
RUN pip install uv --no-cache-dir

# Copy and install base requirements
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# ============================================
# PaddleOCR-VL-1.5 Installation (Bengali Support)
# ============================================
# Step 1: NumPy 1.x lock
RUN uv pip install --system --no-cache numpy==1.26.0

# Step 2: PaddlePaddle 3.2.1 (Bengali support requires this version)
RUN uv pip install --system --no-cache paddlepaddle==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Step 3: Force NumPy 1.x (PaddlePaddle sometimes pulls 2.x)
RUN uv pip install --system --no-cache --force-reinstall numpy==1.26.0

# Step 4: PaddleOCR-VL-1.5
RUN uv pip install --system --no-cache -U "paddleocr[doc-parser]"

# Step 5: Final NumPy fix
RUN uv pip install --system --no-cache --force-reinstall numpy==1.26.0

# Copy application code
COPY app/ ./app/

RUN mkdir -p /app/input /app/output /app/temp

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]