FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

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
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# PyTorch for EasyOCR (CPU version)
RUN uv pip install --system --no-cache torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install --system --no-cache torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu

# Copy application
COPY app/ ./app/

RUN mkdir -p /app/input /app/output /app/temp

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]