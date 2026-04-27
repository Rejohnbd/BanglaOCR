import os
import re
import cv2
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pdf2image import convert_from_path
import easyocr
import warnings
warnings.filterwarnings("ignore")


class VoterOCRProcessor:
    # Class-level OCR reader (shared across instances for speed)
    _ocr_reader = None
    
    def __init__(self, pdf_path: str, output_dir: str, use_gpu: bool = False):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.use_gpu = use_gpu
        
        os.makedirs(output_dir, exist_ok=True)
        self.debug_dir = os.path.join(output_dir, "debug_grids")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.poppler_path = None
        self.ocr = self._get_ocr_reader()
        
        # Stats tracking
        self.stats = {
            "total_pages": 0,
            "total_cells": 0,
            "total_voters": 0,
            "extraction_time": 0
        }

    @classmethod
    def _get_ocr_reader(cls, use_gpu: bool = False):
        """ Lazy load OCR reader once and reuse"""
        if cls._ocr_reader is None:
            cls._ocr_reader = easyocr.Reader(['bn', 'en'], gpu=use_gpu, verbose=False)
        return cls._ocr_reader

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """ Enhance image for better OCR: denoise, contrast, binarization"""
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        #  Denoise - removes noise
        denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        #  CLAHE - Contrast Limited Adaptive Histogram Equalization
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        #  Thresholding for better text detection
        _, binary = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def detect_document_skew(self, image_path: str) -> float:
        """ Detect and correct document skew using edge detection"""
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Hough line detection
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return 0
        
        # Calculate angles of detected lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if -45 < angle < 45:  # Filter near-horizontal lines
                    angles.append(angle)
        
        if angles:
            return np.median(angles)
        return 0

    def correct_skew(self, image_path: str) -> np.ndarray:
        """ Correct skewed document"""
        img = cv2.imread(image_path)
        skew_angle = self.detect_document_skew(image_path)
        
        if abs(skew_angle) < 0.5:
            return img
        
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        corrected = cv2.warpAffine(img, rotation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
        
        return corrected

    def auto_detect_grid_params(self, image_path: str) -> Dict:
        """ Auto-detect grid parameters using image analysis"""
        img = cv2.imread(image_path)
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Edge detection to find grid lines
        edges = cv2.Canny(gray, 50, 150)
        
        # Detect horizontal lines (rows)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 4, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Find row height from line spacing
        row_hist = cv2.reduce(horizontal_lines, 1, cv2.REDUCE_MAX)
        row_peaks = np.where(row_hist > 0)[0]
        
        row_height = 253  # Default
        if len(row_peaks) > 1:
            row_diffs = np.diff(row_peaks)
            row_height = int(np.median(row_diffs[row_diffs > 50]))
        
        return {
            "row_height": max(200, min(row_height, 300)),
            "col_width": 738,
            "left_offset": 74,
            "top_offset": 65,
            "h_gap": 1,
            "v_gap": 1
        }

    def pdf_to_images(self, dpi: int = 200) -> List[str]:
        """Convert PDF to images with proper DPI"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Converting PDF to images (DPI: {dpi})...")
        
        try:
            images = convert_from_path(
                self.pdf_path,
                dpi=dpi,
                fmt='png',
                poppler_path=self.poppler_path
            )
        except Exception as e:
            print(f"[ERROR] Failed to convert PDF: {e}")
            return []
        
        paths = []
        for i, img in enumerate(images):
            p = os.path.join(self.output_dir, f"page_{i+1}.png")
            img.save(p)
            paths.append(p)
        
        self.stats["total_pages"] = len(paths)
        print(f"[] Converted {len(paths)} pages")
        return paths

    def visualize_grid(self, image_path: str, cells: List[Tuple[int, int, int, int]], page_num: int):
        """ Visualize detected grid cells"""
        img = cv2.imread(image_path)
        if img is None:
            return
        
        for idx, (x1, y1, x2, y2) in enumerate(cells):
            # Draw rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
            # Add label
            label = f"Cell {idx+1}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(img, (x1, y1 - label_size[1] - 8), (x1 + label_size[0] + 10, y1), (0, 0, 255), -1)
            cv2.putText(img, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Title
        title = f"Page {page_num} - {len(cells)} Cells"
        cv2.putText(img, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        debug_path = os.path.join(self.debug_dir, f"grid_page_{page_num}.png")
        cv2.imwrite(debug_path, img)
        print(f"[DEBUG] Saved grid visualization: {debug_path}")

    def detect_grid_cells(self, image_path: str, page_num: int) -> List[Tuple[int, int, int, int]]:
        """ Enhanced grid detection with auto-parameters and fallback"""
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        h, w = img.shape[:2]
        
        #  Auto-detect parameters
        params = self.auto_detect_grid_params(image_path)
        
        left_offset = 113
        top_offset = 103
        row_height = 378
        fixed_col_width = 1107
        h_gap = params["h_gap"]
        v_gap = params["v_gap"]
        
        cells = []
        
        # Calculate grid dimensions
        effective_h = h - top_offset
        row_span = row_height + v_gap
        num_rows = max(1, effective_h // row_span)
        
        effective_w = w - left_offset
        col_span = fixed_col_width + h_gap
        max_cols = effective_w // col_span
        num_cols = min(3, max(1, max_cols))
        
        # Generate cells
        for row in range(num_rows):
            y1 = top_offset + row * row_span
            y2 = y1 + row_height
            
            if y2 > h:
                y2 = h
            if y2 - y1 < 150:
                continue
            
            for col in range(num_cols):
                x1 = left_offset + col * col_span
                x2 = x1 + fixed_col_width
                
                if x2 > w:
                    x2 = w
                if x2 - x1 < 150:
                    continue
                
                cell_x1 = max(0, x1 + 1)
                cell_y1 = max(0, y1 + 1)
                cell_x2 = min(w, x2 - 1)
                cell_y2 = min(h, y2 - 1)
                
                if cell_x2 > cell_x1 and cell_y2 > cell_y1:
                    cells.append((cell_x1, cell_y1, cell_x2, cell_y2))
        
        #  Fallback if no cells found
        if len(cells) < 3:
            print(f"Grid detection failed, using text-based fallback")
            cells = self.detect_cells_by_text_distribution(image_path)
        
        self.stats["total_cells"] += len(cells)
        self.visualize_grid(image_path, cells, page_num)
        return cells

    def detect_cells_by_text_distribution(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """ Fallback: Detect cells by text clustering"""
        result = self.ocr.readtext(image_path)
        
        if not result:
            return []
        
        # Extract bounding boxes
        bboxes = []
        for detection in result:
            bbox = detection[0]
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            bboxes.append((min(xs), min(ys), max(xs), max(ys)))
        
        if not bboxes:
            return []
        
        # Cluster by Y coordinate (rows)
        bboxes.sort(key=lambda x: x[1])
        rows = []
        current_row = []
        current_y = bboxes[0][1]
        y_threshold = 80
        
        for bbox in bboxes:
            if abs(bbox[1] - current_y) < y_threshold:
                current_row.append(bbox)
            else:
                if current_row:
                    rows.append(current_row)
                current_row = [bbox]
                current_y = bbox[1]
        
        if current_row:
            rows.append(current_row)
        
        # Create cells from rows
        img = cv2.imread(image_path)
        h, w = img.shape[:2]
        cells = []
        
        for row_bboxes in rows:
            if not row_bboxes:
                continue
            
            row_top = min(b[1] for b in row_bboxes) - 30
            row_bottom = max(b[3] for b in row_bboxes) + 30
            col_width = w // 3
            
            for col in range(3):
                x1 = max(0, col * col_width)
                x2 = min(w, (col + 1) * col_width)
                y1 = max(0, row_top)
                y2 = min(h, row_bottom)
                
                if x2 > x1 and y2 > y1:
                    cells.append((x1, y1, x2, y2))
        
        print(f"[TEXT-BASED] Found {len(cells)} cells from text distribution")
        return cells

    def extract_cell_text(self, image_path: str, cell_bbox: Tuple[int, int, int, int]) -> str:
        """ Extract text with preprocessing"""
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
        
        #  Preprocess cell image
        preprocessed = self.preprocess_image_array(cell_img)
        
        result = self.ocr.readtext(preprocessed, detail=0)
        
        return "\n".join(result) if result else ""

    def preprocess_image_array(self, img_array: np.ndarray) -> np.ndarray:
        """ Preprocess image array for better OCR"""
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Threshold
        _, binary = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def parse_voter_card(self, text: str) -> Dict:
        """Parse voter card - complete working version with proper address extraction"""
        bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        
        # Normalize text - keep original for full_text
        original_text = text
        text = re.sub(r'\n+', '\n', text).strip()
        
        data = {
            "sl": "", "name": "", "voter_no": "", "father_name": "", "mother_name": "",
            "occupation": "", "date_of_birth_bangla": "", "date_of_birth_eng": "",
            "address": "", "full_text": original_text
        }
        
        field_status = {k: False for k in data if k != "full_text"}
        
        # ---- 1. SL (serial) ----
        sl_match = re.search(r'^([০-৯0-9]{1,4})[\.\s]', text)
        if sl_match:
            data["sl"] = sl_match.group(1).strip()
            # Remove any English digits if mixed (keep only Bangla digits)
            if any(c in '0123456789' for c in data["sl"]):
                # Convert English to Bangla
                en2bn = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
                data["sl"] = data["sl"].translate(en2bn)
            field_status["sl"] = bool(data["sl"])
        
        # ---- 2. Name ----
        name_match = re.search(r'নাম:\s*([^\n]+)', text)
        if name_match:
            data["name"] = name_match.group(1).strip()
            field_status["name"] = True
        
        # ---- 3. Voter number ----
        voter_match = re.search(r'ভোটার\s*নং:\s*([^\n]+)', text)
        if voter_match:
            data["voter_no"] = voter_match.group(1).strip()
            field_status["voter_no"] = True
        
        # ---- 4. Father name ----
        father_match = re.search(r'পিতা:\s*([^\n]+?)(?=\n(?:মাতা:|পেশা:|জন্ম|তারিখ|ঠিকানা|$))', text, re.DOTALL)
        if not father_match:
            father_match = re.search(r'পিতা:\s*([^\n]+)', text)
        if father_match:
            data["father_name"] = father_match.group(1).strip()
            field_status["father_name"] = True
        
        # ---- 5. Mother name ----
        mother_match = re.search(r'মাতা:\s*([^\n]+?)(?=\n(?:পিতা:|পেশা:|জন্ম|তারিখ|ঠিকানা|$))', text, re.DOTALL)
        if not mother_match:
            mother_match = re.search(r'মাতা:\s*([^\n]+)', text)
        if mother_match:
            data["mother_name"] = mother_match.group(1).strip()
            field_status["mother_name"] = True
        
        # ---- 6. Occupation ----
        occ_match = re.search(r'পেশা:\s*(.+?)(?=\n(?:জন্ম|তারিখ|ঠিকানা|$))', text, re.DOTALL)
        if occ_match:
            occ = occ_match.group(1).strip().rstrip(',')
            occ = re.split(r'(জন্ম|তারিখ)', occ)[0].strip()
            data["occupation"] = occ
            field_status["occupation"] = bool(occ)
        
        # ---- 7. Date of birth ----
        dob_match = re.search(r'(?:জন্ম\s*)?তারিখ:\s*([^\n]+?)(?=\n(?:ঠিকানা|$))', text, re.DOTALL)
        if dob_match:
            raw_date = dob_match.group(1).strip()
            raw_date = re.sub(r'[,\s]+$', '', raw_date)
            data["date_of_birth_bangla"] = raw_date
            field_status["date_of_birth_bangla"] = True
            
            eng_date = raw_date.translate(bn2en)
            eng_date = re.sub(r'[^0-9/]', '', eng_date)
            
            if eng_date:
                try:
                    parts = eng_date.split('/')
                    if len(parts) == 3:
                        d, m, y = parts
                        if len(y) == 2:
                            y = f"19{y}" if int(y) >= 70 else f"20{y}"
                        dt = datetime.strptime(f"{d}/{m}/{y}", "%d/%m/%Y")
                        data["date_of_birth_eng"] = dt.strftime("%Y-%m-%d")
                        field_status["date_of_birth_eng"] = True
                except:
                    pass
        
        # ==================== IMPROVED ADDRESS EXTRACTION ====================
        address_extracted = False
        
        # Try different patterns in order
        patterns = [
            r'ঠিকানা:\s*(.+?)(?=\n\s*(?:$|\n\s*\n))',  # Until end or double newline
            r'ঠিকানা:\s*(.+)$',                         # Simple to end
            r'ঠিকান:\s*(.+)$',                          # Misspelled version
            r'ঠিকান[া]?\s*:?\s*(.+?)(?=\n(?:নাম:|ভোটার|পিতা:|মাতা:|পেশা:|$))',  # Until next field
        ]
        
        for pattern in patterns:
            addr_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if addr_match:
                addr = addr_match.group(1).strip()
                if addr and len(addr) > 2:
                    addr = re.sub(r'\n+', ' ', addr)
                    addr = re.sub(r'\s+', ' ', addr)
                    addr = re.sub(r'[,\s]+$', '', addr)
                    data["address"] = addr
                    field_status["address"] = True
                    address_extracted = True
                    break
        
        # Fallback: line by line capture
        if not address_extracted:
            lines = text.split('\n')
            addr_parts = []
            capture = False
            
            for line in lines:
                line_clean = line.strip()
                if 'ঠিকানা' in line_clean or 'ঠিকান' in line_clean:
                    capture = True
                    # Extract after colon or take whole line
                    if ':' in line_clean:
                        after = line_clean.split(':', 1)[1].strip()
                        if after:
                            addr_parts.append(after)
                    else:
                        # Remove the address keyword
                        remaining = re.sub(r'ঠিকান[া]?', '', line_clean).strip()
                        if remaining:
                            addr_parts.append(remaining)
                elif capture:
                    # Stop if we hit another field
                    if any(k in line_clean for k in ['নাম:', 'ভোটার:', 'পিতা:', 'মাতা:', 'পেশা:', 'জন্ম:', 'তারিখ:']):
                        break
                    if line_clean and len(line_clean) > 1:
                        addr_parts.append(line_clean)
            
            if addr_parts:
                data["address"] = ' '.join(addr_parts).strip()
                data["address"] = re.sub(r'\s+', ' ', data["address"])
                data["address"] = re.sub(r'[,\s]+$', '', data["address"])
                if data["address"] and len(data["address"]) > 2:
                    field_status["address"] = True
        
        # Final cleanup
        if data["address"]:
            data["address"] = re.sub(r',+', ',', data["address"])
            data["address"] = re.sub(r'\s*,\s*', ', ', data["address"])
        
        # Calculate overall status
        data["status"] = all(field_status.values())
        data["fields"] = field_status
        
        return data

    def process(self, progress_callback=None) -> List[Dict]:
        """ Main processing pipeline with progress tracking"""
        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"BANGLA VOTER OCR - PROCESSING STARTED")
        print(f"{'='*60}")
        print(f"PDF: {self.pdf_path}")
        print(f"Output: {self.output_dir}")
        
        image_paths = self.pdf_to_images(dpi=300)
        if not image_paths:
            return []
        
        total_pages = len(image_paths)
        all_voters = []
        
        for idx, img_path in enumerate(image_paths):
            page_num = idx + 1
            
            #  Report progress
            if progress_callback:
                progress_callback(
                    current_page=page_num,
                    total_pages=total_pages,
                    status="processing",
                    count=len(all_voters)
                )
            print(f"\n[Page {page_num}/{len(image_paths)}] Processing...")
            
            # Detect and extract
            cells = self.detect_grid_cells(img_path, page_num)
            
            if not cells:
                print(f"No cells detected on page {page_num}")
                continue
            
            page_voters = []
            for cell_idx, cell_bbox in enumerate(cells):
                cell_text = self.extract_cell_text(img_path, cell_bbox)
                print(f"[DEBUG] Cell {cell_idx+1}: {cell_text}")
                
                if cell_text and len(cell_text.strip()) > 50:
                    voter_data = self.parse_voter_card(cell_text)
                    
                    if voter_data.get("name") or voter_data.get("voter_no"):
                        voter_data["_source_page"] = page_num
                        voter_data["_source_cell"] = cell_idx + 1
                        page_voters.append(voter_data)
                        print(f"[DEBUG] Cell {cell_idx+1}: Found voter {voter_data.get('name', 'Unknown')[:30]}...")
                        
                        if progress_callback:
                            progress_callback(
                                current_page=page_num,
                                total_pages=total_pages,
                                status="processing",
                                count=len(all_voters) + len(page_voters)
                            )
                        
                        name = voter_data.get('name', 'Unknown')[:25]
                        status = "" if voter_data.get("status") else ""
                        print(f"  {status} Cell {cell_idx+1}: {name}")
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Extracted {len(page_voters)} voters from page {page_num}")
            all_voters.extend(page_voters)
            print(f"Page {page_num}: Extracted {len(page_voters)} voters")
        
        # Save results
        out_path = os.path.join(self.output_dir, "voters.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_voters, f, ensure_ascii=False, indent=2)
        
        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f" PROCESSING COMPLETED")
        print(f"{'='*60}")
        print(f"Total Pages: {self.stats['total_pages']}")
        print(f"Total Cells: {self.stats['total_cells']}")
        print(f"Total Voters: {len(all_voters)}")
        print(f"Time Elapsed: {elapsed:.2f}s")
        print(f"Results: {out_path}")
        print(f"{'='*60}\n")
        
        return all_voters
