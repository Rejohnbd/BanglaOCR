# bkit/main.py
import os
import uuid
import shutil
import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from typing import Dict
import json

from app.voter_ocr_bkit import VoterOCRProcessorBKit

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

tasks: Dict[str, dict] = {}

app = FastAPI(title="Bangla Voter OCR API - bKit Hybrid", version="5.0")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "engine": "Hybrid (EasyOCR + bKit)",
        "timestamp": datetime.now().isoformat()
    }


def process_task(task_id: str, pdf_path: str, output_dir: str):
    logger.info(f"🟢 bKit Task {task_id} started")
    
    try:
        total_pages_count = 0
        
        # 🔥 গুরুত্বপূর্ণ: এখানে total_pages প্যারামিটার যোগ করুন
        def update_progress(current_page, total_pages, status, count=0):
            nonlocal total_pages_count
            total_pages_count = total_pages
            
            if total_pages_count > 0:
                if current_page == 0:
                    percent = 0
                else:
                    percent = int(((current_page - 1) / total_pages_count) * 100)
                
                if status == "processing":
                    percent = min(percent, 99)
            else:
                percent = 0
            
            if status == "completed":
                percent = 100
            
            tasks[task_id].update({
                "status": status,
                "total_page": total_pages_count,
                "current_page": current_page,
                "count": count,
                "progress_percent": percent,
                "total_voters": count
            })
            
            if current_page > 0:
                logger.info(f"Task {task_id}: Page {current_page}/{total_pages_count} ({percent}%) | Voters: {count}")
        
        processor = VoterOCRProcessorBKit(pdf_path, output_dir)
        data = processor.process(progress_callback=update_progress)
        
        tasks[task_id] = {
            "status": "completed",
            "total_voters": len(data),
            "total_page": total_pages_count,
            "current_page": total_pages_count,
            "file": f"{output_dir}/voters.json",
            "completed_at": datetime.now().isoformat(),
            "success": len(data) > 0,
            "progress_percent": 100
        }
        logger.info(f"✅ bKit Task {task_id} completed. Found {len(data)} voters")
    
    except Exception as e:
        logger.error(f"❌ bKit Task {task_id} failed: {str(e)}")
        traceback.print_exc()
        tasks[task_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")
    
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
            "engine": "Hybrid",
            "total_page": 0,
            "current_page": 0,
            "total_voters": 0,
            "progress_percent": 0
        }
        
        background_tasks.add_task(process_task, task_id, pdf_path, output_dir)
        
        return {
            "task_id": task_id,
            "status_url": f"/status/{task_id}",
            "download_url": f"/download/{task_id}",
            "debug_url": f"/debug/{task_id}"
        }
    
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@app.get("/status/{task_id}")
def status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Check if file exists
    if task.get("status") == "processing":
        output_dir = os.path.join("output", task_id)
        json_file = os.path.join(output_dir, "voters.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["total_voters"] = len(data)
                tasks[task_id]["progress_percent"] = 100
                tasks[task_id]["current_page"] = tasks[task_id].get("total_page", 1)
            except:
                pass
    
    return {
        "task_id": task_id,
        "engine": "Hybrid",
        "status": task.get("status"),
        "total_voters": task.get("total_voters", 0),
        "total_page": task.get("total_page", 0),
        "current_page": task.get("current_page", 0),
        "progress_percent": task.get("progress_percent", 0),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
        "error": task.get("error"),
        "download_url": f"/download/{task_id}" if task.get("status") == "completed" else None,
        "debug_url": f"/debug/{task_id}" if task.get("status") == "completed" else None
    }


@app.get("/download/{task_id}")
def download(task_id: str):
    json_path = os.path.join("output", task_id, "voters.json")
    if not os.path.exists(json_path):
        raise HTTPException(404, "Results not found")
    return FileResponse(json_path, media_type="application/json", filename=f"voters_{task_id}.json")


@app.get("/debug/{task_id}")
def debug(task_id: str):
    debug_dir = os.path.join("output", task_id, "debug_grids")
    if not os.path.exists(debug_dir):
        raise HTTPException(404, "Debug grids not found")
    
    import zipfile
    zip_path = os.path.join("temp", f"debug_{task_id}.zip")
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for root, dirs, files in os.walk(debug_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, debug_dir)
                zf.write(file_path, arcname)
    
    return FileResponse(zip_path, media_type="application/zip", filename=f"debug_{task_id}.zip")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")