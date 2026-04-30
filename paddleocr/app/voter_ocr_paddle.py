import os
import re
import cv2
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
from pdf2image import convert_from_path
import warnings
warnings.filterwarnings("ignore")

import paddle

# মেমরি অপ্টিমাইজেশন ফ্ল্যাগ
paddle.set_flags({
    "FLAGS_allocator_strategy": "auto_growth",
    "FLAGS_eager_delete_tensor_gb": 0.0,
    "FLAGS_fraction_of_cpu_memory_to_use": 0.1
})


print("[INFO] Loading voter_ocr_paddle module...")

# PaddleOCR-VL ইম্পোর্ট
try:
    from paddleocr import PaddleOCRVL
    PADDLE_AVAILABLE = True
    print("[INFO] PaddleOCR-VL imported successfully")
except Exception as e:
    PADDLE_AVAILABLE = False
    print(f"[ERROR] PaddleOCR-VL import failed: {e}")


class VoterOCRProcessorPaddle:
    _processor = None
    
    def __init__(self, pdf_path: str, output_dir: str, use_gpu: bool = False):
        print(f"[DEBUG] __init__ STARTED for {pdf_path}")
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        
        os.makedirs(output_dir, exist_ok=True)
        self.debug_dir = os.path.join(output_dir, "debug_grids")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.poppler_path = None
        
        if PADDLE_AVAILABLE:
            print("[DEBUG] Calling _get_processor...")
            self.processor = self._get_processor()
            print("[DEBUG] _get_processor completed")
        else:
            self.processor = None
            print("[ERROR] PaddleOCR-VL not available")
        
        self.stats = {
            "total_pages": 0,
            "total_cells": 0,
            "total_voters": 0,
            "extraction_time": 0
        }
        print(f"[DEBUG] __init__ COMPLETED")

    @classmethod
    def _get_processor(cls):
        """Lazy load PaddleOCR-VL processor - NO PARAMETERS"""
        if cls._processor is None:
            print("[PaddleOCR-VL-1.5] Initializing (Optimized)...")
            # use_layout_detection=False দিলে PP-DocLayoutV3 লোড হবে না
            cls._processor = PaddleOCRVL(use_layout_detection=False, device='cpu')
            print("[PaddleOCR-VL-1.5] Model ready!")
        return cls._processor

    def pdf_to_images(self, dpi: int = 200) -> List[str]:
        """Convert PDF to images"""
        print(f"[DEBUG] pdf_to_images STARTED")
        
        if not os.path.exists(self.pdf_path):
            print(f"[ERROR] PDF not found: {self.pdf_path}")
            return []
        
        try:
            images = convert_from_path(
                self.pdf_path,
                dpi=dpi,
                fmt='png',
                poppler_path=self.poppler_path
            )
        except Exception as e:
            print(f"[ERROR] convert_from_path failed: {e}")
            return []
        
        paths = []
        for i, img in enumerate(images):
            p = os.path.join(self.output_dir, f"page_{i+1}.png")
            img.save(p)
            paths.append(p)
        
        self.stats["total_pages"] = len(paths)
        print(f"[DEBUG] pdf_to_images COMPLETED: {len(paths)} pages")
        return paths

    def detect_grid_cells(self, image_path: str, page_num: int) -> List[Tuple[int, int, int, int]]:
        """Static grid detection"""
        print(f"[DEBUG] detect_grid_cells for page {page_num}")
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        h, w = img.shape[:2]
        # 200 DPI এর জন্য প্যারামিটার
        left_offset = 50
        top_offset = 45
        row_height = 280
        col_width = 500
        h_gap = 5
        v_gap = 5
        
        cells = []
        effective_h = h - top_offset
        row_span = row_height + v_gap
        num_rows = max(1, effective_h // row_span)
        effective_w = w - left_offset
        col_span = col_width + h_gap
        max_cols = effective_w // col_span
        num_cols = min(3, max(1, max_cols))
        
        for row in range(num_rows):
            y1 = top_offset + row * row_span
            y2 = y1 + row_height
            if y2 > h:
                y2 = h
            if y2 - y1 < 100:
                continue
            
            for col in range(num_cols):
                x1 = left_offset + col * col_span
                x2 = x1 + col_width
                if x2 > w:
                    x2 = w
                if x2 - x1 < 100:
                    continue
                cells.append((x1 + 2, y1 + 2, x2 - 2, y2 - 2))
        
        self.stats["total_cells"] += len(cells)
        self.visualize_grid(image_path, cells, page_num)
        return cells

    def visualize_grid(self, image_path: str, cells: List[Tuple[int, int, int, int]], page_num: int):
        """Save grid visualization"""
        img = cv2.imread(image_path)
        if img is None:
            return
        
        for idx, (x1, y1, x2, y2) in enumerate(cells):
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f"Cell {idx+1}", (x1 + 5, y1 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        debug_path = os.path.join(self.debug_dir, f"grid_page_{page_num}.png")
        cv2.imwrite(debug_path, img)
        print(f"[DEBUG] Saved: {debug_path}")

    def extract_cell_text(self, image_path: str, cell_bbox: Tuple[int, int, int, int]) -> str:
        """Extract text using PaddleOCR-VL"""
        img = cv2.imread(image_path)
        if img is None:
            return ""
        
        x1, y1, x2, y2 = cell_bbox
        h, w = img.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x1 >= x2 or y1 >= y2:
            return ""
        
        cell_img = img[y1:y2, x1:x2]
        
        try:
            # PaddleOCRVL PIL Image সাপোর্ট করে না, সরাসরি Numpy Array (RGB) দিতে হবে
            cell_img_rgb = cv2.cvtColor(cell_img, cv2.COLOR_BGR2RGB)
            
            # সরাসরি numpy array পাস করুন
            output = self.processor.predict(cell_img_rgb, prompt="OCR:")
            
            if output and len(output) > 0:
                if hasattr(output[0], 'text'):
                    return output[0].text
                return str(output[0])
            return ""
        except Exception as e:
            print(f"[WARNING] OCR failed: {e}")
            return ""

    def parse_voter_card(self, text: str) -> Dict:
        """Simple parser - extract fields"""
        bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        
        data = {
            "sl": "", "name": "", "voter_no": "", "father_name": "", "mother_name": "",
            "occupation": "", "date_of_birth_bangla": "", "date_of_birth_eng": "",
            "address": "", "full_text": text
        }
        
        # Name extraction
        name_match = re.search(r'নাম:\s*([^\n]+)', text)
        if name_match:
            data["name"] = name_match.group(1).strip()
        
        # Voter number
        voter_match = re.search(r'ভোটার\s*নং:\s*([^\n]+)', text)
        if voter_match:
            data["voter_no"] = voter_match.group(1).strip()
        
        # Father
        father_match = re.search(r'পিতা:\s*([^\n]+)', text)
        if father_match:
            data["father_name"] = father_match.group(1).strip()
        
        # Mother
        mother_match = re.search(r'মাতা:\s*([^\n]+)', text)
        if mother_match:
            data["mother_name"] = mother_match.group(1).strip()
        
        # Address
        addr_match = re.search(r'ঠিকানা:\s*(.+)$', text, re.DOTALL)
        if addr_match:
            addr = addr_match.group(1).strip().replace('\n', ' ')
            data["address"] = addr
        
        return data

    def process(self, progress_callback=None) -> List[Dict]:
        """Main processing pipeline"""
        print(f"\n{'='*60}")
        print(f"[PROCESS] STARTED")
        print(f"{'='*60}")
        print(f"PDF: {self.pdf_path}")
        
        image_paths = self.pdf_to_images(dpi=200)
        if not image_paths:
            print("[ERROR] No images")
            return []
        
        total_pages = len(image_paths)
        all_voters = []
        
        for idx, img_path in enumerate(image_paths):
            page_num = idx + 1
            print(f"\n[PAGE {page_num}/{total_pages}]")
            
            if progress_callback:
                progress_callback(current_page=page_num, total_pages=total_pages, 
                                status="processing", count=len(all_voters))
            
            cells = self.detect_grid_cells(img_path, page_num)
            if not cells:
                continue
            
            for cell_idx, cell_bbox in enumerate(cells):
                cell_text = self.extract_cell_text(img_path, cell_bbox)
                if cell_text and len(cell_text.strip()) > 30:
                    voter_data = self.parse_voter_card(cell_text)
                    if voter_data.get("name") or voter_data.get("voter_no"):
                        voter_data["_source_page"] = page_num
                        voter_data["_source_cell"] = cell_idx + 1
                        all_voters.append(voter_data)
                        
                        if progress_callback:
                            progress_callback(current_page=page_num, total_pages=total_pages,
                                            status="processing", count=len(all_voters))
                        
                        print(f"Cell {cell_idx+1}: {voter_data.get('name', 'Unknown')[:30]}")
        
        out_path = os.path.join(self.output_dir, "voters.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_voters, f, ensure_ascii=False, indent=2)
        
        print(f"\n[PROCESS] COMPLETED: {len(all_voters)} voters")
        return all_voters