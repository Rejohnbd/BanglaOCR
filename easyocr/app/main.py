import os
import uuid
import shutil
import logging
import traceback
import asyncio
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, Optional
import json

from app.voter_ocr import VoterOCRProcessor

# Logging set up
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Task storage
tasks: Dict[str, dict] = {}

app = FastAPI(title="Bangla Voter OCR API", version="2.0")


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len([t for t in tasks.values() if t.get("status") == "processing"])
    }


def process_task(task_id: str, pdf_path: str, output_dir: str):
    """Background processing with progress tracking"""
    logger.info(f"Task {task_id} started")
    
    try:
        # Progress callback function
        def update_progress(current_page, total_pages, status, count=0):
            """Update task progress smoothly based on ~18 voters per page"""
            if total_pages > 0:
                base_percent = ((current_page - 1) / total_pages) * 100
                
                voters_per_page_estimate = 18
                voters_on_current_page = max(0, count - ((current_page - 1) * voters_per_page_estimate))
                
                # Cap current page progress so it doesn't exceed its allocated percentage
                page_progress = min((voters_on_current_page / voters_per_page_estimate), 0.99) * (100 / total_pages)
                
                percent = int(base_percent + page_progress)
                
                # Ensure it stays below 100% while still processing
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
        
        # Initialize processor with improved version
        processor = VoterOCRProcessor(pdf_path, output_dir, use_gpu=False)
        
        # Pass progress callback to processor
        data = processor.process(progress_callback=update_progress)
        
        # Successful completion
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
        
        # Error storage
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
        
        # Cleanup
        try:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
        except:
            pass


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """PDF upload endpoint"""
    
    # Validation
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")
    
    if file.size and file.size > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(413, "File too large (max 100MB)")
    
    # Task ID generate
    task_id = str(uuid.uuid4())
    pdf_path = os.path.join("temp", f"{task_id}.pdf")
    output_dir = os.path.join("output", task_id)
    
    os.makedirs("temp", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # File storage
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Task status update (with progress fields)
        tasks[task_id] = {
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "file_name": file.filename,
            "file_size": file.size,
            "total_page": 0,
            "present_page": 0,
            "count": 0,
            "progress_percent": 0,
            "message": "Initializing PDF conversion..."
        }
        
        # Background process start
        background_tasks.add_task(process_task, task_id, pdf_path, output_dir)
        
        logger.info(f"Task {task_id} created for file: {file.filename} ({file.size} bytes)")
        
        return {
            "task_id": task_id,
            "status_url": f"/status/{task_id}",
            "download_url": f"/download/{task_id}",
            "message": "PDF processing started. Check status_url for progress."
        }
    
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        # Cleanup
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
        except:
            pass
        raise HTTPException(500, f"Upload failed: {str(e)}")


@app.get("/status/{task_id}")
def status(task_id: str):
    """Task status check with progress tracking"""
    task = tasks.get(task_id)
    
    if not task:
        raise HTTPException(404, {"error": "Task not found", "task_id": task_id})
    
    # Check from file if not known
    if task.get("status") == "processing":
        output_dir = os.path.join("output", task_id)
        json_file = os.path.join(output_dir, "voters.json")
        
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "total_page": task.get("total_page", len(data)),
                    "present_page": task.get("present_page", len(data)),
                    "count": len(data),
                    "file": json_file,
                    "completed_at": datetime.now().isoformat(),
                    "progress_percent": 100,
                    "success": len(data) > 0,
                    "message": f"Successfully extracted {len(data)} voters",
                    "download_url": f"/download/{task_id}"
                }
            except Exception as e:
                logger.warning(f"Error reading {json_file}: {e}")
    
    # Return with progress fields (Always returning same keys)
    return {
        "task_id": task_id,
        "status": task.get("status", "pending"),
        "total_page": task.get("total_page", 0),
        "present_page": task.get("present_page", 0),
        "count": task.get("count", 0),
        "progress_percent": task.get("progress_percent", 0),
        "created_at": task.get("created_at", ""),
        "file": task.get("file", ""),
        "completed_at": task.get("completed_at", ""),
        "success": task.get("success", False),
        "message": task.get("message", "Processing..."),
        "download_url": f"/download/{task_id}" if task.get("status") == "completed" else "",
        "error": task.get("error", "")
    }


@app.get("/download/{task_id}")
def download(task_id: str):
    """ Download results """
    task = tasks.get(task_id)
    
    if not task:
        raise HTTPException(404, "Task not found")
    
    json_path = os.path.join("output", task_id, "voters.json")
    
    if not os.path.exists(json_path):
        raise HTTPException(404, "Results not found. Task may still be processing.")
    
    return FileResponse(
        json_path,
        media_type="application/json",
        filename=f"voters_{task_id}.json"
    )


@app.get("/download-debug/{task_id}")
def download_debug_grids(task_id: str):
    """ debug grids download """
    debug_dir = os.path.join("output", task_id, "debug_grids")
    
    if not os.path.exists(debug_dir):
        raise HTTPException(404, "Debug grids not found")
    
    # Create ZIP of debug grids
    import zipfile
    zip_path = os.path.join("temp", f"debug_grids_{task_id}.zip")
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for root, dirs, files in os.walk(debug_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, debug_dir)
                zf.write(file_path, arcname)
    
    return FileResponse(zip_path, media_type="application/zip", filename=f"debug_grids_{task_id}.zip")


@app.get("/tasks")
def list_tasks():
    """ list all tasks """
    return {
        "total": len(tasks),
        "processing": len([t for t in tasks.values() if t.get("status") == "processing"]),
        "completed": len([t for t in tasks.values() if t.get("status") == "completed"]),
        "failed": len([t for t in tasks.values() if t.get("status") == "failed"]),
        "tasks": {
            task_id: {
                "status": task.get("status"),
                "created_at": task.get("created_at"),
                "count": task.get("count"),
                "file_name": task.get("file_name")
            }
            for task_id, task in list(tasks.items())[-20:]  # Last 20 tasks
        }
    }


@app.delete("/cleanup/{task_id}")
def cleanup(task_id: str):
    """ task and file delete """
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    
    try:
        # Remove files
        pdf_path = os.path.join("temp", f"{task_id}.pdf")
        output_dir = os.path.join("output", task_id)
        
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        
        # Remove task
        del tasks[task_id]
        
        logger.info(f"🧹 Task {task_id} cleaned up")
        
        return {"status": "success", "message": f"Task {task_id} cleaned up"}
    
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(500, f"Cleanup failed: {str(e)}")


@app.get("/stats")
def get_stats():
    """ System statistics """
    completed_tasks = [t for t in tasks.values() if t.get("status") == "completed"]
    total_voters = sum(t.get("count", 0) for t in completed_tasks)
    
    return {
        "total_tasks": len(tasks),
        "processing": len([t for t in tasks.values() if t.get("status") == "processing"]),
        "completed": len(completed_tasks),
        "failed": len([t for t in tasks.values() if t.get("status") == "failed"]),
        "total_voters_extracted": total_voters,
        "avg_voters_per_task": total_voters / len(completed_tasks) if completed_tasks else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
