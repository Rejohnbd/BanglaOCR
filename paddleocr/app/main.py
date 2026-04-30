import os
import uuid
import shutil
import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict
import json

from app.voter_ocr_paddle import VoterOCRProcessorPaddle

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Task storage
tasks: Dict[str, dict] = {}

app = FastAPI(title="Bangla Voter OCR API - PaddleOCR", version="1.0")


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "engine": "PaddleOCR",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len([t for t in tasks.values() if t.get("status") == "processing"])
    }


def process_task(task_id: str, pdf_path: str, output_dir: str):
    """Background processing with progress tracking"""
    logger.info(f"🟢 PaddleOCR Task {task_id} started")
    
    try:
        def update_progress(current_page, total_pages, status, count=0):
            if total_pages > 0:
                percent = int(((current_page - 1) / total_pages) * 100)
                if status == "processing":
                    percent = min(percent, 99)
            else:
                percent = 0
            if status == "completed":
                percent = 100
                
            tasks[task_id].update({
                "status": status,
                "total_page": total_pages,
                "present_page": current_page,
                "count": count,
                "progress_percent": percent
            })
            logger.info(f"Task {task_id}: Page {current_page}/{total_pages} ({percent}%) | Voters: {count}")
            pass
        
        processor = VoterOCRProcessorPaddle(pdf_path, output_dir, use_gpu=False)
        logger.info(f"Task {task_id}: Processor created, calling process()...")

        data = processor.process(progress_callback=update_progress)
        logger.info(f"Task {task_id}: process() returned {len(data)} voters")
        
        tasks[task_id] = {
            "status": "completed",
            "total_page": len(data),
            "present_page": len(data),
            "count": len(data),
            "file": f"{output_dir}/voters.json",
            "completed_at": datetime.now().isoformat(),
            "success": len(data) > 0,
            "message": f"Successfully extracted {len(data)} voters",
            "progress_percent": 100
        }
        logger.info(f"Task {task_id} completed. Found {len(data)} voters")
    
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        traceback.print_exc()
        current_task = tasks.get(task_id, {})
        tasks[task_id] = {
            "status": "failed",
            "total_page": current_task.get("total_page", 0),
            "present_page": current_task.get("present_page", 0),
            "count": current_task.get("count", 0),
            "error": str(e),
            "error_type": type(e).__name__,
            "failed_at": datetime.now().isoformat(),
            "message": f"Processing failed: {str(e)}",
            "progress_percent": current_task.get("progress_percent", 0)
        }
        try:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
        except:
            pass


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """PDF upload endpoint"""
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")
    if file.size and file.size > 100 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 100MB)")
    
    task_id = str(uuid.uuid4())
    pdf_path = os.path.join("temp", f"{task_id}.pdf")
    output_dir = os.path.join("output", task_id)
    
    os.makedirs("temp", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        tasks[task_id] = {
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "file_name": file.filename,
            "file_size": file.size,
            "total_page": 0,
            "present_page": 0,
            "count": 0,
            "progress_percent": 0,
            "message": "Initializing PaddleOCR processing..."
        }
        
        background_tasks.add_task(process_task, task_id, pdf_path, output_dir)
        logger.info(f"Task {task_id} created for file: {file.filename} ({file.size} bytes)")
        
        return {
            "task_id": task_id,
            "engine": "PaddleOCR",
            "status_url": f"/status/{task_id}",
            "download_url": f"/download/{task_id}",
            "message": "PaddleOCR processing started. Check status_url for progress."
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        try:
            if os.path.exists(pdf_path): os.remove(pdf_path)
            if os.path.exists(output_dir): shutil.rmtree(output_dir)
        except:
            pass
        raise HTTPException(500, f"Upload failed: {str(e)}")


@app.get("/status/{task_id}")
def status(task_id: str):
    """Task status check with progress tracking"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, {"error": "Task not found", "task_id": task_id})
    
    if task.get("status") == "processing":
        output_dir = os.path.join("output", task_id)
        json_file = os.path.join(output_dir, "voters.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {
                    "task_id": task_id, "engine": "PaddleOCR",
                    "status": "completed",
                    "count": len(data), "progress_percent": 100,
                    "success": len(data) > 0,
                    "message": f"Successfully extracted {len(data)} voters",
                    "download_url": f"/download/{task_id}"
                }
            except Exception as e:
                logger.warning(f"Error reading {json_file}: {e}")
    
    return {
        "task_id": task_id, "engine": "PaddleOCR",
        "status": task.get("status", "pending"),
        "total_page": task.get("total_page", 0),
        "present_page": task.get("present_page", 0),
        "count": task.get("count", 0),
        "progress_percent": task.get("progress_percent", 0),
        "created_at": task.get("created_at", ""),
        "completed_at": task.get("completed_at", ""),
        "success": task.get("success", False),
        "message": task.get("message", "Processing..."),
        "download_url": f"/download/{task_id}" if task.get("status") == "completed" else "",
        "error": task.get("error", "")
    }


@app.get("/download/{task_id}")
def download(task_id: str):
    """Download results"""
    json_path = os.path.join("output", task_id, "voters.json")
    if not os.path.exists(json_path):
        raise HTTPException(404, "Results not found. Task may still be processing.")
    return FileResponse(json_path, media_type="application/json",
                        filename=f"voters_{task_id}.json")


@app.get("/download-debug/{task_id}")
def download_debug_grids(task_id: str):
    """Download debug grid images"""
    debug_dir = os.path.join("output", task_id, "debug_grids")
    if not os.path.exists(debug_dir):
        raise HTTPException(404, "Debug grids not found")
    import zipfile
    zip_path = os.path.join("temp", f"debug_grids_{task_id}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for root, dirs, files in os.walk(debug_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, debug_dir)
                zf.write(file_path, arcname)
    return FileResponse(zip_path, media_type="application/zip",
                        filename=f"debug_grids_{task_id}.zip")


@app.get("/tasks")
def list_tasks():
    """List all tasks"""
    return {
        "engine": "PaddleOCR",
        "total": len(tasks),
        "processing": len([t for t in tasks.values() if t.get("status") == "processing"]),
        "completed": len([t for t in tasks.values() if t.get("status") == "completed"]),
        "failed": len([t for t in tasks.values() if t.get("status") == "failed"]),
        "tasks": {
            tid: {"status": t.get("status"), "created_at": t.get("created_at"),
                   "count": t.get("count"), "file_name": t.get("file_name")}
            for tid, t in list(tasks.items())[-20:]
        }
    }


@app.delete("/cleanup/{task_id}")
def cleanup(task_id: str):
    """Delete task and associated files"""
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    try:
        pdf_path = os.path.join("temp", f"{task_id}.pdf")
        output_dir = os.path.join("output", task_id)
        if os.path.exists(pdf_path): os.remove(pdf_path)
        if os.path.exists(output_dir): shutil.rmtree(output_dir)
        del tasks[task_id]
        logger.info(f"Task {task_id} cleaned up")
        return {"status": "success", "message": f"Task {task_id} cleaned up"}
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(500, f"Cleanup failed: {str(e)}")


@app.get("/stats")
def get_stats():
    """System statistics"""
    completed = [t for t in tasks.values() if t.get("status") == "completed"]
    total_voters = sum(t.get("count", 0) for t in completed)
    return {
        "engine": "PaddleOCR",
        "total_tasks": len(tasks),
        "processing": len([t for t in tasks.values() if t.get("status") == "processing"]),
        "completed": len(completed),
        "failed": len([t for t in tasks.values() if t.get("status") == "failed"]),
        "total_voters_extracted": total_voters,
        "avg_voters_per_task": total_voters / len(completed) if completed else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
