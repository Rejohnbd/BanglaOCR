# bkit/app/voter_ocr_bkit.py - হাইব্রিড সমাধান (EasyOCR + bKit.transform + Custom Cleaner)
import os
import re
import json
import gc
import cv2
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
import tempfile
from pdf2image import convert_from_path
import easyocr
import warnings
warnings.filterwarnings("ignore")

print("[INFO] Loading Hybrid OCR Engine: EasyOCR + bKit + Custom Cleaner...")


class VoterOCRProcessorBKit:
    def __init__(self, pdf_path: str, output_dir: str):
        print(f"[DEBUG] __init__ STARTED for {pdf_path}")
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.debug_dir = os.path.join(output_dir, "debug_grids")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.poppler_path = None
        self.temp_dir = tempfile.gettempdir()
        
        # Initialize EasyOCR (for OCR)
        self.easyocr_reader = None
        self._init_easyocr()
        
        # Initialize bKit for text cleaning (if available)
        self.bkit_available = False
        self.bkit_normalizer = None
        self._init_bkit_cleaner()
        
        self.stats = {"total_pages": 0, "total_cells": 0, "total_voters": 0}
        print(f"[DEBUG] __init__ COMPLETED")
    
    def _init_easyocr(self):
        """Initialize EasyOCR engine"""
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['bn', 'en'], gpu=False, verbose=False)
            print("[INFO] EasyOCR initialized successfully")
        except ImportError as e:
            print(f"[ERROR] EasyOCR not installed: {e}")
            self.easyocr_reader = None
        except Exception as e:
            print(f"[ERROR] EasyOCR init failed: {e}")
            self.easyocr_reader = None
    
    def _init_bkit_cleaner(self):
        """Initialize bKit's transform module for cleaning (no NER/POS)"""
        try:
            from bkit import transform
            
            self.bkit_normalizer = transform.Normalizer(
                normalize_characters=True,
                normalize_zw_characters=True,
                normalize_halant=True,
                normalize_vowel_kar=True,
                normalize_punctuation_spaces=True
            )
            self.bkit_available = True
            print("[INFO] bKit text cleaner (transform) ready.")
        except ImportError:
            print("[INFO] bKit transform not available, using custom cleaner only")
            self.bkit_available = False
        except Exception as e:
            print(f"[WARNING] bKit init failed: {e}, using custom cleaner only")
            self.bkit_available = False
    
    def clean_text_custom(self, text: str) -> str:
        """Basic Bangla text cleaning (no bKit dependencies)"""
        if not text:
            return ""
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common Bangla issues
        replacements = {
            'অা': 'আ',
            'অি': 'ই',
            'অু': 'উ',
            'াা': 'া',
            'িি': 'ি',
            'ুু': 'ু',
            'েে': 'ে',
            'োো': 'ো',
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d]', '', text)
        
        return text.strip()
    
    def clean_text_with_bkit(self, text: str) -> str:
        """Clean text using bKit (if available) or fallback to custom cleaner"""
        if not text:
            return ""
        
        if self.bkit_available and self.bkit_normalizer:
            try:
                cleaned = self.bkit_normalizer(text)
                cleaned = re.sub(r'\s+', ' ', cleaned)
                return cleaned.strip()
            except Exception as e:
                print(f"[WARNING] bKit cleaning failed: {e}, using custom cleaning")
                return self.clean_text_custom(text)
        else:
            return self.clean_text_custom(text)
    
    def fix_bangla_date(self, raw_date: str) -> str:
        """
        Fix Bangla date by adding missing slashes
        Input: "০৯/০৬ ১৯৮২" or "০৯০৬৮২" or "০/০৯১৯৮৭"
        Output: "০৯/০৬/১৯৮২"
        """
        if not raw_date:
            return ""
        
        # Remove any spaces, dots, dashes first
        cleaned = re.sub(r'[.\-\s]+', '/', raw_date)
        
        # Extract only Bangla digits and slashes
        bangla_digits = re.findall(r'[০-৯]+', cleaned)
        
        if len(bangla_digits) >= 3:
            day = bangla_digits[0][:2] if len(bangla_digits[0]) >= 2 else bangla_digits[0].zfill(2)
            month = bangla_digits[1][:2] if len(bangla_digits[1]) >= 2 else bangla_digits[1].zfill(2)
            year = bangla_digits[2]
            if len(year) == 2:
                year = f"19{year}" if int(year) >= 70 else f"20{year}"
            return f"{day}/{month}/{year}"
        
        elif len(bangla_digits) == 2:
            combined = bangla_digits[0]
            year = bangla_digits[1]
            if len(combined) >= 4:
                day = combined[:2]
                month = combined[2:4]
            else:
                day = combined[0] if len(combined) >= 1 else ""
                month = combined[1:3] if len(combined) >= 3 else ""
            day = day.zfill(2) if day else ""
            month = month.zfill(2) if month else ""
            if len(year) == 2:
                year = f"19{year}" if int(year) >= 70 else f"20{year}"
            if day and month and year:
                return f"{day}/{month}/{year}"
        
        elif len(bangla_digits) == 1:
            combined = bangla_digits[0]
            if len(combined) >= 8:
                day = combined[:2]
                month = combined[2:4]
                year = combined[4:8]
                return f"{day}/{month}/{year}"
        
        # এই লাইনটি এখন ফাংশনের ভিতরে সঠিক জায়গায় আছে
        return raw_date
    
    def convert_bangla_to_english_date(self, bangla_date: str) -> str:
        """Convert Bangla date to English YYYY-MM-DD format"""
        bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        
        fixed_bangla = self.fix_bangla_date(bangla_date)
        eng_date = fixed_bangla.translate(bn2en)
        
        try:
            parts = eng_date.split('/')
            if len(parts) == 3:
                d, m, y = parts
                d = d.zfill(2)
                m = m.zfill(2)
                if len(y) == 2:
                    y = f"19{y}" if int(y) >= 70 else f"20{y}"
                dt = datetime.strptime(f"{d}/{m}/{y}", "%d/%m/%Y")
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        return ""

    def pdf_to_images(self, dpi: int = 200) -> List[str]:
        """Convert PDF to images with memory optimization"""
        print(f"[DEBUG] pdf_to_images STARTED (DPI: {dpi})")
        if not os.path.exists(self.pdf_path):
            print(f"[ERROR] PDF not found: {self.pdf_path}")
            return []
        
        try:
            images = convert_from_path(
                self.pdf_path, dpi=dpi, fmt='png', 
                poppler_path=self.poppler_path, thread_count=1
            )
        except Exception as e:
            print(f"[ERROR] convert_from_path failed: {e}")
            return []
        
        paths = []
        for i, img in enumerate(images):
            p = os.path.join(self.output_dir, f"page_{i+1}.png")
            img.save(p)
            paths.append(p)
            img.close()
        
        self.stats["total_pages"] = len(paths)
        print(f"[DEBUG] Converted {len(paths)} pages")
        
        del images
        gc.collect()
        return paths

    def detect_grid_cells(self, image_path: str, page_num: int) -> List[Tuple[int, int, int, int]]:
        """
        FULLY AUTOMATIC grid detection with priority-based methods
        Method 1: Contour detection (best for boxes)
        Method 2: Text clustering (best for voter lists)
        Method 3: Fixed grid (fallback)
        """
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        h, w = img.shape[:2]
        print(f"[DEBUG] Page {page_num}: {w}x{h} - Auto-detecting cells...")
        
        cells = []
        method_used = "None"
        
        # Method 1: Contour detection
        cells = self._detect_by_contours(img, h, w)
        method_used = "Contour Detection"
        
        # Method 2: Text clustering
        if len(cells) < 3:
            cells = self._detect_by_text_clustering(image_path, h, w)
            method_used = "Text Clustering"
        
        # Method 3: Fixed grid
        if len(cells) < 3:
            cells = self._fixed_grid(h, w)
            method_used = "Fixed Grid"
        
        self._save_debug_grid(img, cells, page_num, method_used, h, w)
        
        print(f"[DEBUG] Method: {method_used}, Cells: {len(cells)}")
        return cells

    def _detect_by_contours(self, img, h, w) -> List[Tuple[int, int, int, int]]:
        """Method 1: Contour-based detection"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        for thresh_val in [200, 150, 100]:
            _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            boxes = []
            min_area = (w * h) * 0.01
            max_area = (w * h) * 0.15
            
            for contour in contours:
                x, y, bw, bh = cv2.boundingRect(contour)
                area = bw * bh
                
                if min_area < area < max_area and bw > 100 and bh > 100:
                    aspect = bw / bh if bh > 0 else 0
                    if 0.3 < aspect < 3.0:
                        boxes.append((x, y, x + bw, y + bh))
            
            if len(boxes) >= 3:
                boxes.sort(key=lambda b: (b[1], b[0]))
                return boxes[:18]
        
        return []

    def _detect_by_text_clustering(self, image_path: str, h, w) -> List[Tuple[int, int, int, int]]:
        """Method 2: Text clustering using EasyOCR"""
        if self.easyocr_reader is None:
            return []
        
        try:
            result = self.easyocr_reader.readtext(image_path)
            if not result or len(result) < 5:
                return []
            
            bboxes = []
            for detection in result:
                bbox = detection[0]
                xs = [point[0] for point in bbox]
                ys = [point[1] for point in bbox]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                if x2 - x1 > 20 and y2 - y1 > 10:
                    bboxes.append((x1, y1, x2, y2))
            
            if len(bboxes) < 5:
                return []
            
            bboxes.sort(key=lambda b: b[1])
            
            rows = []
            current_row = [bboxes[0]]
            y_threshold = 60
            
            for bbox in bboxes[1:]:
                if abs(bbox[1] - current_row[-1][1]) < y_threshold:
                    current_row.append(bbox)
                else:
                    rows.append(current_row)
                    current_row = [bbox]
            if current_row:
                rows.append(current_row)
            
            if not rows:
                return []
            
            row_heights = []
            for row_bboxes in rows:
                y_coords = [b[3] - b[1] for b in row_bboxes]
                if y_coords:
                    row_heights.append(max(y_coords))
            avg_row_height = sum(row_heights) / len(row_heights) if row_heights else 150
            
            cells = []
            for row_bboxes in rows:
                if len(row_bboxes) < 2:
                    continue
                
                row_bboxes.sort(key=lambda b: b[0])
                row_y_center = sum((b[1] + b[3])/2 for b in row_bboxes) / len(row_bboxes)
                num_cols = min(3, len(row_bboxes))
                if num_cols < 2:
                    continue
                
                col_width = w // 3 if len(row_bboxes) >= 3 else (row_bboxes[-1][2] - row_bboxes[0][0]) / num_cols
                y1 = max(0, int(row_y_center - avg_row_height * 0.8))
                y2 = min(h, int(row_y_center + avg_row_height * 0.8))
                
                for col in range(num_cols):
                    if col < len(row_bboxes):
                        center_x = (row_bboxes[col][0] + row_bboxes[col][2]) / 2
                    else:
                        center_x = (col + 0.5) * col_width
                    
                    x1 = max(0, int(center_x - col_width * 0.6))
                    x2 = min(w, int(center_x + col_width * 0.6))
                    
                    if x2 - x1 > 100 and y2 - y1 > 60:
                        cells.append((x1, y1, x2, y2))
            
            return cells
        except Exception as e:
            print(f"[WARNING] Text clustering failed: {e}")
            return []

    def _fixed_grid(self, h, w) -> List[Tuple[int, int, int, int]]:
        """Method 3: Fixed grid (3 columns, 6 rows)"""
        top_margin = int(h * 0.16)
        bottom_margin = int(h * 0.05)
        left_margin = int(w * 0.05)
        
        cell_w = int((w - 2 * left_margin) / 3)
        cell_h = int((h - top_margin - bottom_margin) / 6)
        
        cells = []
        for row in range(6):
            for col in range(3):
                x1 = left_margin + (col * cell_w)
                y1 = top_margin + (row * cell_h)
                x2 = x1 + cell_w
                y2 = y1 + cell_h
                pad = 5
                cells.append((x1 + pad, y1 + pad, x2 - pad, y2 - pad))
        
        return cells

    def _save_debug_grid(self, img, cells, page_num: int, method_used: str, h: int, w: int):
        """Save debug image"""
        debug_img = img.copy()
        
        for idx, (x1, y1, x2, y2) in enumerate(cells):
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(debug_img, f"Cell {idx+1}", (x1 + 5, y1 + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        title = f"Page {page_num} | Method: {method_used} | Cells: {len(cells)}"
        cv2.putText(debug_img, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        info = f"Cleaner: {'bKit' if self.bkit_available else 'Custom'}"
        cv2.putText(debug_img, info, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        debug_path = os.path.join(self.debug_dir, f"grid_page_{page_num}.png")
        cv2.imwrite(debug_path, debug_img)
        print(f"[DEBUG] Saved: {debug_path}")

    def extract_cell_text(self, image_path: str, cell_bbox: Tuple[int, int, int, int]) -> str:
        """Extract text using EasyOCR + clean with hybrid cleaner"""
        if self.easyocr_reader is None:
            return ""
        
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
        
        # Save temp image
        temp_path = os.path.join(self.temp_dir, f"cell_{datetime.now().timestamp()}.png")
        cv2.imwrite(temp_path, cell_img)
        
        try:
            # OCR with EasyOCR
            result = self.easyocr_reader.readtext(temp_path, detail=0)
            if not result:
                return ""
            
            raw_text = "\n".join(result)
            
            # Clean with hybrid method (bKit or custom)
            cleaned_text = self.clean_text_with_bkit(raw_text)
            
            return cleaned_text.strip()
        except Exception as e:
            print(f"[WARNING] OCR failed: {e}")
            return ""
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            gc.collect()

    def parse_voter_card(self, text: str) -> Dict:
        """Parse voter card text into JSON with status and fields tracking"""
        # Add newlines before field markers for better parsing
        text = re.sub(r'(নাম:|ভোটার নং:|পিতা:|মাতা:|পেশা:|জন্ম তারিখ:|জন্ম তারখ:|ঠিকানা:)', r'\n\1', text)
        text = re.sub(r'\n+', '\n', text).strip()
        
        # Clean text with hybrid method
        text = self.clean_text_with_bkit(text)
        
        bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        
        data = {
            "sl": "", "name": "", "voter_no": "", "father_name": "", "mother_name": "",
            "occupation": "", "date_of_birth_bangla": "", "date_of_birth_eng": "",
            "address": "", "full_text": text
        }
        
        field_status = {
            "sl": False, "name": False, "voter_no": False, "father_name": False,
            "mother_name": False, "occupation": False, "date_of_birth_bangla": False,
            "date_of_birth_eng": False, "address": False
        }
        
        # Extract SL (serial number)
        sl_match = re.search(r'^([০-৯0-9]{2,4})[\.\s]', text)
        if not sl_match:
            sl_match = re.search(r'([০-৯0-9]{2,4})[\.\s]*(?:নাম|Name)', text)
        if sl_match:
            sl_val = sl_match.group(1)
            if any(c in '0123456789' for c in sl_val):
                en2bn = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
                sl_val = sl_val.translate(en2bn)
            data["sl"] = sl_val
            field_status["sl"] = True
        
        # Extract Name
        name_match = re.search(r'নাম:\s*([^\n]+?)(?=\s*(?:ভোটার নং:|পিতা:|মাতা:|পেশা:|জন্ম|ঠিকানা:|$))', text, re.DOTALL)
        if name_match:
            data["name"] = name_match.group(1).strip()
            field_status["name"] = True
        
        # Extract Voter No
        voter_match = re.search(r'ভোটার\s*নং:\s*([^\n]+?)(?=\s*(?:পিতা:|মাতা:|পেশা:|জন্ম|ঠিকানা:|$))', text, re.DOTALL)
        if voter_match:
            data["voter_no"] = voter_match.group(1).strip()
            field_status["voter_no"] = True
        
        # Extract Father Name
        father_match = re.search(r'পিতা:\s*([^\n]+?)(?=\s*(?:মাতা:|পেশা:|জন্ম|ঠিকানা:|$))', text, re.DOTALL)
        if father_match:
            data["father_name"] = father_match.group(1).strip()
            field_status["father_name"] = True
        
        # Extract Mother Name
        mother_match = re.search(r'মাতা:\s*([^\n]+?)(?=\s*(?:পেশা:|জন্ম|ঠিকানা:|$))', text, re.DOTALL)
        if mother_match:
            data["mother_name"] = mother_match.group(1).strip()
            field_status["mother_name"] = True
        
        # Extract Occupation
        occ_match = re.search(r'পেশা:\s*([^\n]+?)(?=\s*(?:জন্ম|ঠিকানা:|$))', text, re.DOTALL)
        if occ_match:
            occ = occ_match.group(1).strip().rstrip(',')
            data["occupation"] = occ
            field_status["occupation"] = True if occ else False
        
        # Extract Date of Birth
        dob_match = re.search(r'(?:জন্ম\s*(?:তারিখ|তারখ):)\s*([^\n]+?)(?=\s*(?:ঠিকানা:|$))', text, re.DOTALL)
        if dob_match:
            raw_date = dob_match.group(1).strip()
            raw_date = re.sub(r'[,\s]+$', '', raw_date)
            
            # Fix date format
            fixed_date = self.fix_bangla_date(raw_date)  # "০৯/০৬ ১৯৮২" → "০৯/০৬/১৯
            data["date_of_birth_bangla"] = fixed_date
            field_status["date_of_birth_bangla"] = True if fixed_date else False
            
            # Convert to English date
            eng_date = self.convert_bangla_to_english_date(fixed_date)
            if eng_date:
                data["date_of_birth_eng"] = eng_date
                field_status["date_of_birth_eng"] = True
        
        # Extract Address
        addr_match = re.search(r'ঠিকানা:\s*(.+?)$', text, re.DOTALL)
        if addr_match:
            addr = addr_match.group(1).strip()
            addr = re.sub(r'\s+', ' ', addr)
            data["address"] = addr
            field_status["address"] = True if addr else False
        
        # Calculate overall status
        data["status"] = all(field_status.values())
        data["fields"] = field_status
        
        return data

    def process(self, progress_callback=None) -> List[Dict]:
        """Main processing pipeline with early page count notification"""
        if self.easyocr_reader is None:
            print("[ERROR] No OCR engine available!")
            return []
        
        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"[PROCESS] BANGLA VOTER OCR - Hybrid Engine")
        print(f"{'='*60}")
        print(f"PDF: {self.pdf_path}")
        print(f"Cleaner: {'bKit' if self.bkit_available else 'Custom'}")
        
        # 🔥 Step 1: প্রথমে ইমেজ কনভার্ট করুন (total_pages জানার জন্য)
        image_paths = self.pdf_to_images(dpi=200)
        if not image_paths:
            return []
        
        total_pages = len(image_paths)
        
        # 🔥 Step 2: প্রোগ্রেস কলব্যাক দিয়ে total_pages জানিয়ে দিন (স্টার্ট এ)
        if progress_callback:
            progress_callback(
                current_page=0,           # 0 পেজ, শুধু total_pages জানানোর জন্য
                total_pages=total_pages,   # মোট পেজ সংখ্যা
                status="processing", 
                count=0
            )
        
        all_voters = []
        
        for idx, img_path in enumerate(image_paths):
            page_num = idx + 1
            print(f"\n[PAGE {page_num}/{total_pages}] Processing...")
            
            if progress_callback:
                progress_callback(
                    current_page=page_num, 
                    total_pages=total_pages, 
                    status="processing", 
                    count=len(all_voters)
                )
            
            cells = self.detect_grid_cells(img_path, page_num)
            
            if not cells:
                print(f"[WARNING] No cells detected on page {page_num}")
                continue
            
            page_voters = []
            for cell_idx, cell_bbox in enumerate(cells):
                cell_text = self.extract_cell_text(img_path, cell_bbox)
                
                if cell_text and len(cell_text.strip()) > 30:
                    voter_data = self.parse_voter_card(cell_text)
                    if voter_data.get("name") or voter_data.get("voter_no"):
                        voter_data["_source_page"] = page_num
                        voter_data["_source_cell"] = cell_idx + 1
                        page_voters.append(voter_data)
                        
                        if progress_callback:
                            progress_callback(
                                current_page=page_num, 
                                total_pages=total_pages, 
                                status="processing", 
                                count=len(all_voters) + len(page_voters)
                            )
                        
                        name_preview = voter_data.get('name', 'Unknown')[:30]
                        status_icon = "✅" if voter_data.get("status") else "⚠️"
                        print(f"  {status_icon} Cell {cell_idx+1}: {name_preview}")
                else:
                    print(f"  ⚠️ Cell {cell_idx+1}: No text (len={len(cell_text) if cell_text else 0})")
            
            print(f"📊 Page {page_num}: Extracted {len(page_voters)} voters")
            all_voters.extend(page_voters)
            gc.collect()
        
        # Save results
        out_path = os.path.join(self.output_dir, "voters.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_voters, f, ensure_ascii=False, indent=2)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f"✅ PROCESSING COMPLETED")
        print(f"{'='*60}")
        print(f"Total Pages: {total_pages}")
        print(f"Total Voters: {len(all_voters)}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Results: {out_path}")
        print(f"{'='*60}\n")
        
        # 🔥 শেষ কলব্যাক (completed)
        if progress_callback:
            progress_callback(
                current_page=total_pages, 
                total_pages=total_pages, 
                status="completed", 
                count=len(all_voters)
            )
        
        return all_voters