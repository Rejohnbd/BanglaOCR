# Bangla Voter OCR

A high-performance Python tool for extracting structured voter information from Bangladeshi voter ID documents (PDF). It leverages EasyOCR with Bangla and English language support, combined with OpenCV-based image preprocessing, to accurately detect grid-based voter card layouts and parse key fields such as name, voter number, father/mother name, date of birth, occupation, and address.

The application is served as a **FastAPI REST API** with asynchronous background processing, real-time progress tracking, and Docker-ready deployment.

---

## Features

- **Bangla & English OCR** — Powered by EasyOCR with dual-language (`bn`, `en`) support for mixed-script voter documents.
- **PDF-to-Image Conversion** — Converts multi-page PDFs to high-resolution images (configurable DPI) via `pdf2image` and Poppler.
- **Intelligent Grid Detection** — Automatically detects voter card grid layouts using edge detection and morphological operations, with a text-clustering fallback for non-standard layouts.
- **Image Preprocessing Pipeline** — Applies denoising, CLAHE contrast enhancement, Otsu binarization, and skew correction for optimal OCR accuracy.
- **Structured Data Extraction** — Parses 9 voter fields (serial, name, voter number, father, mother, occupation, DOB in Bangla/English, address) with regex-based extraction and multi-pattern fallback.
- **Async Background Processing** — Upload a PDF and poll for progress; processing runs in the background with per-page and per-voter progress reporting.
- **Debug Visualization** — Saves annotated grid overlay images for each page to aid in debugging and validation.
- **REST API** — Full CRUD-style API with endpoints for upload, status, download, task listing, cleanup, and system statistics.
- **Docker Support** — Production-ready `Dockerfile` and `docker-compose.yml` with health checks, resource limits, and volume mounts.

---

## Technology Stack

| Category            | Technology                                                    |
| ------------------- | ------------------------------------------------------------- |
| **Language**         | Python 3.10+                                                 |
| **Web Framework**    | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn           |
| **OCR Engine**       | [EasyOCR](https://github.com/JaidedAI/EasyOCR) (Bangla + English) |
| **Image Processing** | [OpenCV](https://opencv.org/) (`opencv-python`)              |
| **PDF Conversion**   | [pdf2image](https://github.com/Belval/pdf2image) + Poppler  |
| **Deep Learning**    | PyTorch (CPU by default; GPU optional)                       |
| **Containerization** | Docker, Docker Compose                                       |

---

## Prerequisites

- **Python** 3.10 or higher
- **Poppler** — Required by `pdf2image` for PDF rendering.
  - **Ubuntu/Debian:** `sudo apt-get install poppler-utils`
  - **macOS:** `brew install poppler`
  - **Windows:** Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add the `bin/` directory to your system `PATH`.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/bangla-ocr.git
cd bangla-ocr
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The default `requirements.txt` installs PyTorch CPU. For GPU acceleration, install the appropriate CUDA version of PyTorch from [pytorch.org](https://pytorch.org/get-started/locally/).

### 4. Docker (Alternative)

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

---

## Usage

### Starting the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
python -m app.main
```

### API Endpoints

#### Upload a PDF

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

#### Check Processing Status

```bash
curl http://localhost:8000/status/{task_id}
```

**Response:**

```json
{
  "task_id": "a1b2c3d4-...",
  "status": "processing",
  "total_page": 5,
  "present_page": 3,
  "count": 42,
  "progress_percent": 58,
  "message": "Processing..."
}
```

#### Download Results

```bash
curl -O http://localhost:8000/download/{task_id}
```

Returns a JSON file containing an array of extracted voter records.

#### Other Endpoints

| Method   | Endpoint                  | Description                          |
| -------- | ------------------------- | ------------------------------------ |
| `GET`    | `/health`                 | Health check with active task count  |
| `GET`    | `/tasks`                  | List all tasks (last 20)             |
| `GET`    | `/stats`                  | System statistics and totals         |
| `GET`    | `/download-debug/{id}`    | Download debug grid images (ZIP)     |
| `DELETE` | `/cleanup/{id}`           | Delete task data and output files    |

### Sample Output

Each extracted voter record follows this structure:

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
  "fields": { "sl": true, "name": true, "...": "..." },
  "_source_page": 1,
  "_source_cell": 1
}
```

---

## Project Structure

```
bangla-ocr/
├── app/
│   ├── main.py              # FastAPI application — REST API entry point
│   ├── voter_ocr.py         # Core OCR processor (image pipeline, grid detection, text parsing)
│   └── check_status.py      # Utility script to poll task status
├── input/                   # Place input PDF files here
├── output/                  # Processing results and debug images
├── temp/                    # Temporary files (uploaded PDFs)
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Multi-service orchestration config
├── requirements.txt         # Python dependencies
├── .gitignore
├── .dockerignore
└── README.md
```

### Key Modules

| File             | Responsibility                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| `app/main.py`     | Defines the FastAPI app with endpoints for upload, status polling, download, cleanup, and stats. Manages background task lifecycle and progress callbacks. |
| `app/voter_ocr.py`| Contains `VoterOCRProcessor` — the core class handling PDF→image conversion, image preprocessing, grid cell detection, OCR text extraction, and voter card field parsing with regex. |

---

## Configuration

| Parameter          | Default | Description                                    |
| ------------------ | ------- | ---------------------------------------------- |
| `--host`           | `0.0.0.0` | Server bind address                          |
| `--port`           | `8000`    | Server port                                  |
| `dpi`              | `300`     | PDF-to-image conversion resolution           |
| `use_gpu`          | `False`   | Enable GPU acceleration for EasyOCR/PyTorch  |
| Max upload size    | `100 MB`  | Enforced at the upload endpoint              |

---

## License

This project is provided as-is for educational and internal use. See `LICENSE` for details if applicable.
