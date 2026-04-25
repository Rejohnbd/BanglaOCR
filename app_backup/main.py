# file: main.py

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

from app.voter_ocr import VoterOCRProcessor

# ✅ লগিং সেটআপ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


tasks: Dict[str, dict] = {}

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


def process_task(task_id, pdf_path, output_dir):
    logger.info(f"🟢 Task {task_id} started")
    try:
        processor = VoterOCRProcessor(pdf_path, output_dir)
        data = processor.process()

        tasks[task_id] = {
            "status": "completed",
            "count": len(data),
            "file": f"{output_dir}/voters.json",
            "completed_at": datetime.now().isoformat()
        }
        logger.info(f"✅ Task {task_id} completed. Found {len(data)} voters")

    except Exception as e:
        logger.error(f"❌ Task {task_id} failed: {str(e)}")
        traceback.print_exc()
        tasks[task_id] = {"status": "failed", "error": str(e)}


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF allowed")

    task_id = str(uuid.uuid4())
    pdf_path = f"temp/{task_id}.pdf"
    output_dir = f"output/{task_id}"

    os.makedirs("temp", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    tasks[task_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "file_name": file.filename
    }

    background_tasks.add_task(process_task, task_id, pdf_path, output_dir)

    logger.info(f"📤 Task {task_id} created for file: {file.filename}")

    return {"task_id": task_id,  "status_url": f"/status/{task_id}", "download_url": f"/download/{task_id}" }


@app.get("/status/{task_id}")
def status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return {"error": "not found"}
    
    # ✅ প্রসেসিং থাকলে কতটা হয়েছে তার ইন্ডিকেশন দিতে
    if task["status"] == "processing":
        # চেক করুন আউটপুট ফাইল ইতিমধ্যে তৈরি হয়েছে কিনা
        output_dir = f"output/{task_id}"
        temp_file = f"output/{task_id}/voters.json"
        if os.path.exists(temp_file):
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "status": "completed",
                "count": len(data),
                "message": "Task completed (detected from file)"
            }
    
    return task


@app.get("/download/{task_id}")
def download(task_id: str):
    task = tasks.get(task_id)

    if not task:
        raise HTTPException(404, "Task not found")
    
    if task["status"] != "completed":
        # চেক করুন ফাইল ইতিমধ্যে আছে কিনা
        json_path = f"output/{task_id}/voters.json"
        if os.path.exists(json_path):
            return FileResponse(json_path)
        raise HTTPException(404, "Task not completed yet")

    return FileResponse(task["file"])

@app.get("/tasks")
def list_tasks():
    """সব টাস্কের স্ট্যাটাস দেখুন"""
    return {
        task_id: {
            "status": task.get("status"),
            "created_at": task.get("created_at"),
            "count": task.get("count") if task.get("status") == "completed" else None
        }
        for task_id, task in tasks.items()
    }