# passport-ocr/app/main.py
import os
import uuid
import shutil
import logging
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import json

from .passport_ocr import FastPassportOCRProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

tasks: Dict[str, dict] = {}

app = FastAPI(title="Complete Passport OCR API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "healthy", "engine": "Complete Passport OCR", "timestamp": datetime.now().isoformat()}


@app.post("/extract")
async def extract_passport(file: UploadFile = File(...)):
    """Extract complete passport information"""
    
    filename = file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith('.jpg') or filename.endswith('.jpeg') or filename.endswith('.png')):
        raise HTTPException(400, "Only PDF, JPG, JPEG, PNG files are allowed")
    
    file_type = "pdf" if filename.endswith('.pdf') else "image"
    task_id = str(uuid.uuid4())
    output_dir = os.path.join("output", task_id)
    os.makedirs(output_dir, exist_ok=True)
    
    file_ext = filename.split('.')[-1]
    file_path = os.path.join(output_dir, f"uploaded.{file_ext}")
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Set generate_debug=True for debug images, False to disable
        processor = FastPassportOCRProcessor(file_path, output_dir, file_type)
        result = processor.process(generate_debug=False)  # ← Change to False to disable debug images
        
        result["task_id"] = task_id
        result["file_name"] = file.filename
        result["processed_at"] = datetime.now().isoformat()
        
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise HTTPException(500, f"Processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")