import os
import uuid
import shutil
import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      
    ],
    allow_credentials=True,
    allow_methods=["*"],              
    allow_headers=["*"],              
    expose_headers=["*"],
)

# Base URL for constructing full URLs
BASE_URL = os.getenv("BASE_URL", "http://localhost:8002")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "engine": "Hybrid (EasyOCR + bKit)",
        "timestamp": datetime.now().isoformat()
    }


# def process_task(task_id: str, pdf_path: str, output_dir: str):
#     logger.info(f"bKit Task {task_id} started")
    
#     try:
#         total_pages_count = 0
        
#         # গুরুত্বপূর্ণ: এখানে total_pages প্যারামিটার যোগ করুন
#         def update_progress(current_page, total_pages, status, count=0):
#             nonlocal total_pages_count
#             total_pages_count = total_pages
            
#             if total_pages_count > 0:
#                 if current_page == 0:
#                     percent = 0
#                 else:
#                     page_percent = (current_page / total_pages_count) * 100
#                     percent = int(min(page_percent, 99))
                
#                 if status == "processing":
#                     percent = min(percent, 99)
#             else:
#                 percent = 0
            
#             if status == "completed":
#                 percent = 100
            
#             tasks[task_id].update({
#                 "status": status,
#                 "total_page": total_pages_count,
#                 "current_page": current_page,
#                 "count": count,
#                 "progress_percent": percent,
#                 "total_voters": count
#             })
            
#             if current_page > 0:
#                 logger.info(f"Task {task_id}: Page {current_page}/{total_pages_count} ({percent}%) | Voters: {count}")
        
#         processor = VoterOCRProcessorBKit(pdf_path, output_dir)
#         data = processor.process(progress_callback=update_progress)
        
#         tasks[task_id] = {
#             "status": "completed",
#             "total_voters": len(data),
#             "total_page": total_pages_count,
#             "current_page": total_pages_count,
#             "file": f"{output_dir}/voters.json",
#             "completed_at": datetime.now().isoformat(),
#             "success": len(data) > 0,
#             "progress_percent": 100
#         }
#         logger.info(f"bKit Task {task_id} completed. Found {len(data)} voters")
    
#     except Exception as e:
#         logger.error(f"bKit Task {task_id} failed: {str(e)}")
#         traceback.print_exc()
#         tasks[task_id] = {
#             "status": "failed",
#             "error": str(e),
#             "failed_at": datetime.now().isoformat()
#         }

# bkit/main.py - process_task ফাংশন আপডেট

# def process_task(task_id: str, pdf_path: str, output_dir: str):
#     logger.info(f"bKit Task {task_id} started")
    
#     try:
#         total_pages_count = 0
#         total_cells_expected = 0
#         total_cells_processed = 0
        
#         def update_progress(current_page, total_pages, status, count=0):
#             nonlocal total_pages_count, total_cells_expected, total_cells_processed
#             total_pages_count = total_pages
            
#             # Expected cells per page (based on detected or default 18)
#             if total_cells_expected == 0 and total_pages > 0:
#                 total_cells_expected = total_pages * 18  # Assume 18 cells per page
            
#             if total_cells_expected > 0:
#                 # Calculate progress based on cells processed
#                 # Each cell found contributes to progress
#                 if current_page > 0:
#                     # Estimate cells processed in current page
#                     cells_in_page = min(18, count - ((current_page - 1) * 18))
#                     total_cells_processed = ((current_page - 1) * 18) + cells_in_page
#                     percent = int((total_cells_processed / total_cells_expected) * 100)
#                     percent = min(percent, 99)
#                 else:
#                     percent = 0
#             else:
#                 percent = 0
            
#             if status == "completed":
#                 percent = 100
            
#             tasks[task_id].update({
#                 "status": status,
#                 "total_page": total_pages_count,
#                 "current_page": current_page,
#                 "count": count,
#                 "progress_percent": percent,
#                 "total_voters": count,
#                 "total_cells_expected": total_cells_expected,
#                 "total_cells_processed": total_cells_processed
#             })
            
#             if current_page > 0:
#                 logger.info(f"Task {task_id}: Page {current_page}/{total_pages_count} | Cells: {total_cells_processed}/{total_cells_expected} ({percent}%) | Voters: {count}")
        
#         processor = VoterOCRProcessorBKit(pdf_path, output_dir)
#         data = processor.process(progress_callback=update_progress)
        
#         tasks[task_id] = {
#             "status": "completed",
#             "total_voters": len(data),
#             "total_page": total_pages_count,
#             "current_page": total_pages_count,
#             "file": f"{output_dir}/voters.json",
#             "completed_at": datetime.now().isoformat(),
#             "success": len(data) > 0,
#             "progress_percent": 100,
#             "total_cells_expected": total_cells_expected,
#             "total_cells_processed": total_cells_expected
#         }
#         logger.info(f"bKit Task {task_id} completed. Found {len(data)} voters")
    
#     except Exception as e:
#         logger.error(f"bKit Task {task_id} failed: {str(e)}")
#         traceback.print_exc()
#         tasks[task_id] = {
#             "status": "failed",
#             "error": str(e),
#             "failed_at": datetime.now().isoformat()
#         }

@app.get("/output/{task_id}/debug_grids/{filename}")
def get_debug_image(task_id: str, filename: str):
    """Serve debug grid images directly"""
    # Security: prevent directory traversal
    if '..' in filename or not filename.endswith('.png'):
        raise HTTPException(400, "Invalid filename")
    
    image_path = os.path.join("output", task_id, "debug_grids", filename)
    
    if not os.path.exists(image_path):
        raise HTTPException(404, "Image not found")
    
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=filename
    )


def process_task(task_id: str, pdf_path: str, output_dir: str):
    logger.info(f"bKit Task {task_id} started")
    
    try:
        total_pages_count = 0
        total_cells_expected = 0
        total_cells_processed = 0
        
        def update_progress(current_page, total_pages, status, count=0):
            nonlocal total_pages_count, total_cells_expected, total_cells_processed
            total_pages_count = total_pages
            
            # Expected cells per page (based on detected or default 18)
            if total_cells_expected == 0 and total_pages > 0:
                total_cells_expected = total_pages * 18  # Assume 18 cells per page
            
            # Calculate progress percentage
            if total_cells_expected > 0 and status != "completed":
                if current_page > 0:
                    # Estimate cells processed in current page
                    cells_so_far = count  # Each voter represents one cell with text
                    total_cells_processed = cells_so_far
                    percent = int((total_cells_processed / total_cells_expected) * 100)
                    percent = min(percent, 99)
                else:
                    percent = 0
            else:
                percent = 0
            
            if status == "completed":
                percent = 100
                total_cells_processed = total_cells_expected
            
            # Update task status
            tasks[task_id].update({
                "status": status,
                "total_page": total_pages_count,
                "current_page": current_page,
                "count": count,
                "progress_percent": percent,
                "total_voters": count,
                "total_cells_expected": total_cells_expected,
                "total_cells_processed": total_cells_processed
            })
            
            if current_page > 0:
                logger.info(f"Task {task_id}: Page {current_page}/{total_pages_count} | Voters: {count}/{total_cells_expected} ({percent}%)")
        
        # Initialize processor
        processor = VoterOCRProcessorBKit(pdf_path, output_dir)
        data = processor.process(progress_callback=update_progress)
        
        # Final task completion
        tasks[task_id] = {
            "status": "completed",
            "total_voters": len(data),
            "total_page": total_pages_count,
            "current_page": total_pages_count,
            "file": f"{output_dir}/voters.json",
            "completed_at": datetime.now().isoformat(),
            "success": len(data) > 0,
            "progress_percent": 100,
            "total_cells_expected": total_cells_expected,
            "total_cells_processed": len(data)  # Actual voters found
        }
        logger.info(f"bKit Task {task_id} completed. Found {len(data)} voters")
    
    except Exception as e:
        logger.error(f" bKit Task {task_id} failed: {str(e)}")
        traceback.print_exc()
        tasks[task_id] = {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "failed_at": datetime.now().isoformat()
        }
        
        # Cleanup on failure
        try:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
        except:
            pass


# @app.get("/tasks")
# def list_tasks():
#     """List all tasks with their current status"""
#     all_tasks = tasks
    
#     total = len(all_tasks)
#     processing = len([t for t in all_tasks.values() if t.get("status") == "processing"])
#     completed = len([t for t in all_tasks.values() if t.get("status") == "completed"])
#     failed = len([t for t in all_tasks.values() if t.get("status") == "failed"])
    
#     # Prepare task list (last 20 tasks)
#     task_list = {}
#     for task_id, task in list(all_tasks.items())[-20:]:
#         task_list[task_id] = {
#             "status": task.get("status"),
#             "created_at": task.get("created_at"),
#             "completed_at": task.get("completed_at"),
#             "total_voters": task.get("total_voters", 0),
#             "total_page": task.get("total_page", 0),
#             "file_name": task.get("file_name"),
#             "progress_percent": task.get("progress_percent", 0)
#         }
    
#     return {
#         "total": total,
#         "processing": processing,
#         "completed": completed,
#         "failed": failed,
#         "tasks": task_list
#     }

@app.get("/tasks")
def list_tasks(status_filter: str = None, limit: int = 20):
    """
    List all tasks with optional filters
    - status_filter: 'processing', 'completed', 'failed' (optional)
    - limit: number of tasks to return (default 20)
    """
    all_tasks = tasks
    
    # Apply status filter if provided
    if status_filter:
        filtered_tasks = {k: v for k, v in all_tasks.items() if v.get("status") == status_filter}
    else:
        filtered_tasks = all_tasks
    
    total = len(filtered_tasks)
    processing = len([t for t in filtered_tasks.values() if t.get("status") == "processing"])
    completed = len([t for t in filtered_tasks.values() if t.get("status") == "completed"])
    failed = len([t for t in filtered_tasks.values() if t.get("status") == "failed"])
    
    # Sort by created_at (newest first) and limit
    sorted_tasks = sorted(
        filtered_tasks.items(), 
        key=lambda x: x[1].get("created_at", ""), 
        reverse=True
    )[:limit]
    
    task_list = {}
    for task_id, task in sorted_tasks:
        task_list[task_id] = {
            "status": task.get("status"),
            "created_at": task.get("created_at"),
            "completed_at": task.get("completed_at"),
            "total_voters": task.get("total_voters", 0),
            "total_page": task.get("total_page", 0),
            "file_name": task.get("file_name"),
            "progress_percent": task.get("progress_percent", 0)
        }
    
    return {
        "total": total,
        "processing": processing,
        "completed": completed,
        "failed": failed,
        "tasks": task_list
    }

@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")
    
    task_id = str(uuid.uuid4())
    
    # PDF ফাইল output ডিরেক্টরির ভিতরে সেভ করুন
    output_dir = os.path.join("output", task_id)
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_path = os.path.join(output_dir, "uploaded_file.pdf")
    temp_dir = os.path.join("temp", task_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # PDF ফাইল সরাসরি output ডিরেক্টরিতে সেভ করুন
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        tasks[task_id] = {
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "file_name": file.filename,  # PDF filename store
            "engine": "Hybrid",
            "total_page": 0,
            "current_page": 0,
            "total_voters": 0,
            "progress_percent": 0,
            "pdf_path": pdf_path
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


# @app.get("/status/{task_id}")
# def status(task_id: str):
#     task = tasks.get(task_id)
#     if not task:
#         raise HTTPException(404, "Task not found")
    
#     # Check if file exists (completed but not updated)
#     if task.get("status") == "processing":
#         output_dir = os.path.join("output", task_id)
#         json_file = os.path.join(output_dir, "voters.json")
#         if os.path.exists(json_file):
#             try:
#                 with open(json_file, 'r', encoding='utf-8') as f:
#                     data = json.load(f)
#                 tasks[task_id]["status"] = "completed"
#                 tasks[task_id]["total_voters"] = len(data)
#                 tasks[task_id]["progress_percent"] = 100
#                 tasks[task_id]["current_page"] = tasks[task_id].get("total_page", 1)
#                 tasks[task_id]["total_cells_processed"] = tasks[task_id].get("total_cells_expected", 18)
#                 tasks[task_id]["completed_at"] = datetime.now().isoformat()
#             except Exception as e:
#                 logger.warning(f"Error reading json file: {e}")
    
#     # Calculate cell-based progress if still processing
#     progress_percent = task.get("progress_percent", 0)
#     total_voters = task.get("total_voters", 0)
#     total_page = task.get("total_page", 0)
#     current_page = task.get("current_page", 0)
    
#     # If processing and have page info, calculate more accurate progress
#     if task.get("status") == "processing" and total_page > 0:
#         # Expected voters per page (can be dynamic based on actual detection)
#         expected_per_page = 18
#         expected_total = total_page * expected_per_page
        
#         if expected_total > 0:
#             # Calculate progress based on voters found vs expected
#             cell_progress = (total_voters / expected_total) * 100
#             progress_percent = min(int(cell_progress), 99)
            
#             # Update task with more accurate progress
#             tasks[task_id]["progress_percent"] = progress_percent
    
#     return {
#         "task_id": task_id,
#         "engine": "Hybrid",
#         "status": task.get("status"),
#         "total_voters": total_voters,
#         "total_page": total_page,
#         "current_page": current_page,
#         "progress_percent": progress_percent,
#         "created_at": task.get("created_at"),
#         "completed_at": task.get("completed_at"),
#         "error": task.get("error"),
#         "download_url": f"/download/{task_id}" if task.get("status") == "completed" else None,
#         "debug_url": f"/debug/{task_id}" if task.get("status") == "completed" else None
#     }

@app.get("/status/{task_id}")
def status(task_id: str):
    """Task status check with progress tracking"""
    task = tasks.get(task_id)
    if not task:
        # Return proper error response
        raise HTTPException(status_code=404, detail={
            "error": "Task not found",
            "task_id": task_id,
            "message": "The task may have expired or the server was restarted. Please upload the file again."
        })
    
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
                tasks[task_id]["completed_at"] = datetime.now().isoformat()
            except Exception as e:
                logger.warning(f"Error reading json file: {e}")
    
    return {
        "task_id": task_id,
        "engine": "Hybrid",
        "status": task.get("status", "pending"),
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


# @app.get("/download/{task_id}")
# def download(task_id: str):
#     json_path = os.path.join("output", task_id, "voters.json")
#     if not os.path.exists(json_path):
#         raise HTTPException(404, "Results not found")
#     return FileResponse(json_path, media_type="application/json", filename=f"voters_{task_id}.json")

@app.get("/download/{task_id}")
def download(task_id: str):
    """Download complete result with full URLs"""
    output_dir = os.path.join("output", task_id)
    
    # Check if task exists
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Check if results exist
    json_path = os.path.join(output_dir, "voters.json")
    if not os.path.exists(json_path):
        raise HTTPException(404, "Results not found")
    
    # Load voters data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            voters_data = json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Error reading results: {str(e)}")
    
    # Get original PDF info
    pdf_path = os.path.join(output_dir, "uploaded_file.pdf")
    pdf_exists = os.path.exists(pdf_path)
    pdf_filename = task.get('file_name', 'uploaded_file.pdf')
    
    # Collect debug grid images with FULL URLs
    debug_dir = os.path.join(output_dir, "debug_grids")
    debug_images = []
    
    if os.path.exists(debug_dir):
        for file in sorted(os.listdir(debug_dir)):
            if file.endswith('.png'):
                debug_images.append({
                    "name": file,
                    "page": file.replace('grid_page_', '').replace('.png', ''),
                    "url": f"{BASE_URL}/output/{task_id}/debug_grids/{file}"  # Full URL
                })
    
    # Calculate statistics
    total_voters = len(voters_data)
    voters_with_all_fields = sum(1 for v in voters_data if v.get('status', False))
    
    # Prepare response with FULL URLs
    response_data = {
        "task_id": task_id,
        "status": task.get("status"),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
        "file": {
            "name": pdf_filename,
            "exists": pdf_exists,
            "size_bytes": os.path.getsize(pdf_path) if pdf_exists else 0,
            "url": f"{BASE_URL}/download-pdf/{task_id}" if pdf_exists else None  # Full URL
        },
        "debug_grids": debug_images,
        "data": voters_data,
        "summary": {
            "total_voters": total_voters,
            "total_pages": task.get("total_page", 0),
            "total_voters_expected": task.get("total_page", 0) * 18,
            "success_rate": f"{(voters_with_all_fields / total_voters * 100):.1f}%" if total_voters > 0 else "0%",
            "extraction_time_seconds": task.get("extraction_time", 0)
        }
    }
    
    return JSONResponse(content=response_data)

@app.get("/download-pdf/{task_id}")
def download_pdf(task_id: str):
    """Download the original PDF file with CORS headers"""
    pdf_path = os.path.join("output", task_id, "uploaded_file.pdf")
    
    if not os.path.exists(pdf_path):
        # Fallback to temp location
        old_pdf_path = os.path.join("temp", f"{task_id}.pdf")
        if os.path.exists(old_pdf_path):
            pdf_path = old_pdf_path
        else:
            raise HTTPException(404, "PDF file not found")
    
    task = tasks.get(task_id, {})
    filename = task.get('file_name', f"uploaded_file.pdf")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/output/{task_id}/debug_grids/{filename}")
def get_debug_image(task_id: str, filename: str):
    """Serve debug grid images directly with CORS headers"""
    # Security: prevent directory traversal
    if '..' in filename or not filename.endswith('.png'):
        raise HTTPException(400, "Invalid filename")
    
    image_path = os.path.join("output", task_id, "debug_grids", filename)
    
    if not os.path.exists(image_path):
        raise HTTPException(404, "Image not found")
    
    # Return with proper CORS headers
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=filename,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/download-pdf/{task_id}")
def download_pdf(task_id: str):
    """Download the original PDF file"""
    pdf_path = os.path.join("temp", f"{task_id}.pdf")
    
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF file not found")
    
    task = tasks.get(task_id, {})
    filename = task.get('file_name', f"document_{task_id}.pdf")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )


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