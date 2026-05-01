# bkit/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# সিস্টেম ডিপেন্ডেন্সি - প্যাকেজ লিস্ট আপডেট ও পুনরায় চেষ্টা
RUN apt-get clean && \
    apt-get update --fix-missing && \
    apt-get install -y \
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

# uv ইন্সটল (দ্রুত প্যাকেজ ম্যানেজার)
RUN pip install uv --no-cache-dir

# Python ডিপেন্ডেন্সি ইন্সটল
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# অ্যাপ্লিকেশন কোড কপি
COPY app/ ./app/

RUN mkdir -p /app/input /app/output /app/temp

# bKit OCR-এর জন্য 8002 পোর্ট
EXPOSE 8002

# হেলথ চেক
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# মেমোরি অপটিমাইজেশনের জন্য এনভায়রনমেন্ট ভেরিয়েবল
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV PYTHONGC=1

# 🔥 CMD ঠিক করুন - main.py রুটে আছে
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--limit-max-requests", "1000"]