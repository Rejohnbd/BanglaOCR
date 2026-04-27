# Bangla Voter OCR

A Python-based tool for extracting structured voter information from Bangladeshi voter ID documents (PDF). This monorepo hosts **two independent OCR services** — choose the engine that best fits your accuracy and performance needs.

| Service | Engine | Port | Best For |
|---------|--------|------|----------|
| **easyocr/** | [EasyOCR](https://github.com/JaidedAI/EasyOCR) | `8000` | Lightweight, fast on CPU |
| **paddleocr/** | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | `8001` | Higher accuracy, better layout detection |

Both services expose an identical REST API, making it easy to swap engines without changing client code.

---

## Features

- **Bangla & English OCR** — Dual-language support for mixed-script voter documents
- **PDF-to-Image Conversion** — High-resolution (300 DPI) via `pdf2image` + Poppler
- **Grid Detection** — Automatic voter card grid layout detection with fallback strategies
- **Image Preprocessing** — Denoising, contrast enhancement, and binarization (EasyOCR service)
- **Layout Analysis** — PPStructure-based layout detection (PaddleOCR service)
- **Structured Extraction** — Parses 9 fields: serial, name, voter number, father, mother, occupation, DOB (Bangla/English), address
- **Async Processing** — Upload a PDF and poll for real-time progress
- **Debug Visualization** — Annotated grid overlay images per page
- **Docker Ready** — Each service has its own `Dockerfile` and `docker-compose.yml`

---

## Technology Stack

| Category | EasyOCR Service | PaddleOCR Service |
|----------|----------------|-------------------|
| **Language** | Python 3.10+ | Python 3.10+ |
| **Web Framework** | FastAPI + Uvicorn | FastAPI + Uvicorn |
| **OCR Engine** | EasyOCR 1.7 | PaddleOCR 2.8 + PPStructure |
| **Deep Learning** | PyTorch (CPU) | PaddlePaddle (CPU/GPU) |
| **Image Processing** | OpenCV | OpenCV |
| **PDF Conversion** | pdf2image + Poppler | pdf2image + Poppler |
| **Containerization** | Docker | Docker |

---

## Prerequisites

- **Python** 3.10+
- **Poppler** — Required by `pdf2image`:
  - **Ubuntu/Debian:** `sudo apt-get install poppler-utils`
  - **macOS:** `brew install poppler`
  - **Windows:** Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add `bin/` to `PATH`

---

## Installation

### Option 1: Docker (Recommended)

```bash
# EasyOCR service (port 8000)
cd easyocr
docker-compose up --build

# PaddleOCR service (port 8001)
cd paddleocr
docker-compose up --build
```

### Option 2: Local Setup

```bash
# Clone the repo
git clone https://github.com/your-username/bangla-ocr.git
cd bangla-ocr

# --- EasyOCR ---
cd easyocr
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# --- PaddleOCR ---
cd paddleocr
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## API Reference

Both services share the same endpoint structure. Replace the base URL/port as needed.

### Upload a PDF

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/voter_list.pdf"
```

**Response:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status_url": "/status/a1b2c3d4-...",
  "download_url": "/download/a1b2c3d4-...",
  "message": "PDF processing started. Check status_url for progress."
}
```

### Check Status

```bash
curl http://localhost:8000/status/{task_id}
```

### Download Results

```bash
curl -O http://localhost:8000/download/{task_id}
```

### All Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload PDF for processing |
| `GET` | `/status/{id}` | Task status with progress |
| `GET` | `/download/{id}` | Download extracted JSON |
| `GET` | `/download-debug/{id}` | Download debug grid images (ZIP) |
| `GET` | `/tasks` | List all tasks (last 20) |
| `GET` | `/stats` | System statistics |
| `DELETE` | `/cleanup/{id}` | Delete task and files |

### Sample Output

```json
{
  "sl": "১",
  "name": "মোঃ আব্দুল করিম",
  "voter_no": "১২৩৪৫৬৭৮৯০",
  "father_name": "মোঃ রহিম উদ্দিন",
  "mother_name": "মোসাঃ রহিমা বেগম",
  "occupation": "কৃষি",
  "date_of_birth_bangla": "০১/০১/১৯৮০",
  "date_of_birth_eng": "1980-01-01",
  "address": "গ্রাম: পূর্বপাড়া, পোস্ট: ধানখেত",
  "status": true,
  "_source_page": 1,
  "_source_cell": 1
}
```

---

## Project Structure

```
bangla-ocr/
├── README.md
├── .gitignore
│
├── easyocr/                         # EasyOCR Service (port 8000)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # FastAPI entry point
│       └── voter_ocr.py             # EasyOCR processor
│
└── paddleocr/                       # PaddleOCR Service (port 8001)
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .dockerignore
    ├── requirements.txt
    └── app/
        ├── main.py                  # FastAPI entry point
        └── voter_ocr_paddle.py      # PaddleOCR processor
```

---

## Configuration

| Parameter | EasyOCR | PaddleOCR | Description |
|-----------|---------|-----------|-------------|
| Port | `8000` | `8001` | Default service port |
| DPI | `300` | `300` | PDF conversion resolution |
| GPU | `False` | `False` | Enable GPU acceleration |
| Max Upload | `100 MB` | `100 MB` | File size limit |

---

## License

This project is provided as-is for educational and internal use.
