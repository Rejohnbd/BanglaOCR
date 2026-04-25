# app/voter_ocr.py - গ্রিড ভিজুয়ালাইজেশন সহ সম্পূর্ণ ভার্সন

import os
import re
import cv2
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
from pdf2image import convert_from_path
import easyocr

class VoterOCRProcessor:
    def __init__(self, pdf_path: str, output_dir: str):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.poppler_path = None
        
        # Create debug directory for grid visualization
        self.debug_dir = os.path.join(output_dir, "debug_grids")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        import warnings
        warnings.filterwarnings("ignore")
        self.ocr = easyocr.Reader(['bn', 'en'], gpu=False, verbose=False)

    def pdf_to_images(self, dpi: int = 200) -> List[str]:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Converting PDF to images...")
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            fmt='png',
            poppler_path=self.poppler_path
        )
        paths = []
        for i, img in enumerate(images):
            p = os.path.join(self.output_dir, f"page_{i+1}.png")
            img.save(p)
            paths.append(p)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Converted {len(paths)} pages")
        return paths

    def visualize_grid(self, image_path: str, cells: List[Tuple[int, int, int, int]], page_num: int):
        """
        Draw red boxes around detected grid cells and save visualization
        """
        img = cv2.imread(image_path)
        
        if img is None:
            print(f"[WARNING] Could not read image: {image_path}")
            return
        
        # Draw each cell with red border
        for idx, (x1, y1, x2, y2) in enumerate(cells):
            # Draw rectangle in red (BGR: 0,0,255)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 1)
            
            # Add cell number in top-left corner
            label = f"Cell {idx+1}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(img, (x1, y1 - label_size[1] - 5), (x1 + label_size[0] + 10, y1), (0, 0, 255), -1)
            cv2.putText(img, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add title with cell count
        title = f"Page {page_num} - Detected {len(cells)} Cells"
        cv2.putText(img, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Save the visualized image
        debug_path = os.path.join(self.debug_dir, f"grid_page_{page_num}.png")
        cv2.imwrite(debug_path, img)
        print(f"[DEBUG] Grid visualization saved to: {debug_path}")
        
        return debug_path

    def detect_grid_cells(self, image_path: str, page_num: int) -> List[Tuple[int, int, int, int]]:
        """
        Detect grid cells with fixed row height, fixed column width,
        and configurable gaps between cells (both horizontally and vertically)
        """
        img = cv2.imread(image_path)
        h, w = img.shape[:2]                     # h = উচ্চতা, w = প্রস্থ
        
        # ===== কনফিগারেবল অফসেট (শুরুর অবস্থান) =====
        left_offset = 74     # বাম দিক থেকে কত পিক্সেল পরে গ্রিড শুরু হবে
        top_offset = 65      # উপরের দিক থেকে কত পিক্সেল পরে গ্রিড শুরু হবে
        
        left_offset = min(left_offset, w - 100)
        top_offset = min(top_offset, h - 100)
        
        # ===== ফিক্সড সেলের আকার ও ফাঁকা স্থান (gap) =====
        row_height = 253           # প্রতিটি সেলের উচ্চতা
        fixed_col_width = 738      # প্রতিটি সেলের প্রস্থ
        
        horizontal_gap = 1        # দুইটি কলামের মাঝে কত পিক্সেল ফাঁকা থাকবে (অনুভূমিক দূরত্ব)
        vertical_gap = 1          # দুইটি সারির মাঝে কত পিক্সেল ফাঁকা থাকবে (উল্লম্ব দূরত্ব)
        
        # কতগুলো সারি বসবে তা বের করি (উচ্চতা ও ফাঁকাসহ)
        effective_h = h - top_offset
        # প্রতিটি সারি দখল করবে: row_height + vertical_gap
        row_span = row_height + vertical_gap
        num_rows = max(1, effective_h // row_span)
        
        # কতগুলো কলাম বসবে (প্রস্থ ও ফাঁকাসহ)
        effective_w = w - left_offset
        col_span = fixed_col_width + horizontal_gap
        max_possible_cols = effective_w // col_span
        num_cols = min(3, max_possible_cols)   # সর্বোচ্চ ৩ কলাম
        
        cells = []
        
        # প্রতিটি সারির জন্য লুপ
        for row in range(num_rows):
            # সেলের উর্ধ্ব সীমানা Y1 (টপ অফসেট + সারি নম্বর × (সেল উচ্চতা+গ্যাপ))
            y1 = top_offset + row * (row_height + vertical_gap)
            # সেলের নিম্ন সীমানা Y2 (কেবল সেলের উচ্চতা যোগ করে, গ্যাপ বাদে)
            y2 = y1 + row_height
            # নিশ্চিত করুন Y2 ইমেজের সীমা অতিক্রম না করে
            if y2 > h:
                y2 = h
            if y2 - y1 < 200:
                continue
            
            # প্রতিটি কলামের জন্য লুপ
            for col in range(num_cols):
                # সেলের বাম সীমানা X1 (বাম অফসেট + কলাম নম্বর × (সেল প্রস্থ+গ্যাপ))
                x1 = left_offset + col * (fixed_col_width + horizontal_gap)
                # সেলের ডান সীমানা X2 (কেবল সেলের প্রস্থ যোগ করে)
                x2 = x1 + fixed_col_width
                if x2 > w:
                    x2 = w
                if x2 - x1 < 200:
                    continue
                
                # প্যাডিং (টেক্সটকে বর্ডার থেকে দূরে রাখতে)
                pad_x = 1
                pad_y = 1
                cell_x1 = max(0, x1 + pad_x)
                cell_y1 = max(0, y1 + pad_y)
                cell_x2 = min(w, x2 - pad_x)
                cell_y2 = min(h, y2 - pad_y)
                
                if cell_x2 > cell_x1 and cell_y2 > cell_y1:
                    cells.append((cell_x1, cell_y1, cell_x2, cell_y2))
        
        # ফোলব্যাক (যদি সেল না পাওয়া যায়)
        if len(cells) < 3:
            cells = self.detect_cells_by_text_distribution(image_path)
        
        self.visualize_grid(image_path, cells, page_num)
        return cells

    def detect_cells_by_text_distribution(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """
        Fallback: Detect cells by analyzing where text is present
        """
        result = self.ocr.readtext(image_path)
        
        if not result:
            print(f"[DEBUG] No text found for text-based detection")
            return []
        
        # Get bounding boxes of all text
        bboxes = []
        for detection in result:
            bbox = detection[0]
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            bboxes.append((min(xs), min(ys), max(xs), max(ys)))
        
        if not bboxes:
            return []
        
        # Group by Y coordinate to identify rows
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
        
        print(f"[DEBUG] Text-based detection found {len(rows)} rows")
        
        # Create cells based on text distribution
        img = cv2.imread(image_path)
        h, w = img.shape[:2]
        cells = []
        
        for row_idx, row_bboxes in enumerate(rows):
            if not row_bboxes:
                continue
            
            row_bboxes.sort(key=lambda x: x[0])
            
            # Estimate row boundaries
            row_top = min(b[1] for b in row_bboxes) - 30
            row_bottom = max(b[3] for b in row_bboxes) + 30
            
            # Divide row into 3 columns
            col_width = w // 3
            
            for col in range(3):
                x1 = col * col_width
                x2 = (col + 1) * col_width
                
                # Add padding
                pad = 10
                cell_x1 = max(0, x1 + pad)
                cell_x2 = min(w, x2 - pad)
                cell_y1 = max(0, row_top)
                cell_y2 = min(h, row_bottom)
                
                if cell_x2 > cell_x1 and cell_y2 > cell_y1:
                    cells.append((cell_x1, cell_y1, cell_x2, cell_y2))
        
        return cells

    def extract_cell_text(self, image_path: str, cell_bbox: Tuple[int, int, int, int]) -> str:
        """Extract text from a specific cell region"""
        img = cv2.imread(image_path)
        x1, y1, x2, y2 = cell_bbox
        
        h, w = img.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x1 >= x2 or y1 >= y2:
            return ""
        
        cell_img = img[y1:y2, x1:x2]
        
        result = self.ocr.readtext(cell_img, detail=0)
        print(f"extract_cell_text result : {result}")
        if not result:
            return ""
        
        return "\n".join(result)

    # def parse_voter_card(self, text: str) -> Dict:
    #     """Parse voter card using line-by-line scanning (robust, no complex regex)"""
    #     bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        
    #     # Clean up text
    #     text = re.sub(r'\n+', '\n', text).strip()
    #     lines = [line.strip() for line in text.split('\n') if line.strip()]
        
    #     data = {
    #         "sl": "",
    #         "name": "",
    #         "voter_no": "",
    #         "father_name": "",
    #         "mother_name": "",
    #         "occupation": "",
    #         "date_of_birth_bangla": "",
    #         "date_of_birth_eng": "",
    #         "address": "",
    #         "full_text": text
    #     }
        
    #     # Field markers (keywords) in order of priority
    #     field_map = {
    #         "name": "নাম:",
    #         "voter_no": "ভোটার নং:",
    #         "father_name": "পিতা:",
    #         "mother_name": "মাতা:",
    #         "occupation": "পেশা:",
    #         "date_of_birth_bangla": "তারিখ:",
    #         "address": "ঠিকানা:"
    #     }
        
    #     # First, try to extract SL (serial) from the very beginning
    #     if lines and re.match(r'^\d{1,4}[\.\s]', lines[0]):
    #         sl_match = re.match(r'^(\d{1,4})', lines[0])
    #         if sl_match:
    #             data["sl"] = sl_match.group(1)
        
    #     # Scan each line for field markers
    #     for i, line in enumerate(lines):
    #         for field, marker in field_map.items():
    #             if marker in line:
    #                 # Extract value after the marker
    #                 value = line.split(marker, 1)[1].strip()
                    
    #                 # If field is occupation, stop at any keyword that indicates next field
    #                 if field == "occupation":
    #                     # Remove trailing "জন্ম তারিখ" or "তারিখ" if accidentally included
    #                     value = re.split(r'(জন্ম|তারিখ|ঠিকানা)', value)[0].strip()
                    
    #                 data[field] = value
    #                 break
        
    #     # Special handling for multi-line address (if not captured fully)
    #     if data["address"] == "":
    #         addr_lines = []
    #         capture = False
    #         for line in lines:
    #             if "ঠিকানা:" in line:
    #                 capture = True
    #                 # Extract after marker
    #                 addr_lines.append(line.split("ঠিকানা:", 1)[1].strip())
    #             elif capture and not any(m in line for m in ["নাম:", "ভোটার নং:", "পিতা:", "মাতা:", "পেশা:", "তারিখ:", "ঠিকানা:"]):
    #                 addr_lines.append(line)
    #             elif capture and any(m in line for m in ["নাম:", "ভোটার নং:", "পিতা:", "মাতা:", "পেশা:", "তারikh:"]):
    #                 break
    #         if addr_lines:
    #             data["address"] = " ".join(addr_lines)
        
    #     # Clean occupation (remove any date leftovers)
    #     if data["occupation"]:
    #         data["occupation"] = re.sub(r'\s*(জন্ম|তারিখ).*$', '', data["occupation"]).strip()
        
    #     # Convert Bangla date to English
    #     if data["date_of_birth_bangla"]:
    #         raw = data["date_of_birth_bangla"]
    #         eng = raw.translate(bn2en)
    #         eng = re.sub(r'[^0-9/]', '', eng)  # keep only digits and slashes
    #         data["date_of_birth_eng"] = eng
    #         try:
    #             parts = eng.split('/')
    #             if len(parts) == 3:
    #                 if len(parts[2]) == 2:
    #                     year = int(parts[2])
    #                     parts[2] = f"19{year}" if year >= 70 else f"20{year}"
    #                 dt = datetime.strptime("/".join(parts), "%d/%m/%Y")
    #                 data["date_of_birth_eng"] = dt.strftime("%Y-%m-%d")
    #         except:
    #             pass
        
    #     # Ensure sl contains only digits (optional: convert Bangla digits)
    #     if data["sl"]:
    #         data["sl"] = data["sl"].translate(bn2en).strip()
        
    #     return data

    def parse_voter_card(self, text: str) -> Dict:
        """Parse voter card - preserves Bangla digits, tracks field extraction status"""
        bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        
        # Normalize text
        text = re.sub(r'\n+', '\n', text).strip()
        
        # Initialize data with full_text
        data = {
            "sl": "", "name": "", "voter_no": "", "father_name": "", "mother_name": "",
            "occupation": "", "date_of_birth_bangla": "", "date_of_birth_eng": "",
            "address": "", "full_text": text
        }
        
        # Track which fields were successfully extracted
        field_status = {
            "sl": False, "name": False, "voter_no": False, "father_name": False,
            "mother_name": False, "occupation": False, "date_of_birth_bangla": False,
            "date_of_birth_eng": False, "address": False
        }
        
        # ---- 1. SL (serial) - PRESERVE BANGLA DIGITS ----
        sl_match = re.search(r'^(\d{1,4})[\.\s]', text)
        if not sl_match:
            # Try with Bangla digits
            sl_match = re.search(r'^([০-৯]{1,4})[\.\s]', text)
        if sl_match:
            data["sl"] = sl_match.group(1).strip()  # Keep original Bangla digits
            field_status["sl"] = True
        
        # ---- 2. Name ----
        name_match = re.search(r'নাম:\s*([^\n]+)', text, re.IGNORECASE)
        if name_match:
            data["name"] = name_match.group(1).strip()
            field_status["name"] = True
        
        # ---- 3. Voter number (preserve Bangla digits) ----
        voter_match = re.search(r'ভোটার\s*নং:\s*([^\n]+)', text, re.IGNORECASE)
        if voter_match:
            data["voter_no"] = voter_match.group(1).strip()
            field_status["voter_no"] = True
        
        # ---- 4. Father name (handles line break after "পিতা:") ----
        father_match = re.search(r'পিতা:\s*\n?\s*([^\n]+?)(?=\s*(?:মাতা:|পেশা:|জন্ম|তারিখ|ঠিকানা:|ঠিকান:|$))', text, re.IGNORECASE | re.DOTALL)
        if not father_match:
            father_match = re.search(r'পিতা:\s*([^\n]+)', text, re.IGNORECASE)
        if father_match:
            data["father_name"] = father_match.group(1).strip()
            field_status["father_name"] = True
        else:
            # Fallback: line-by-line after "পিতা:"
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'পিতা:' in line:
                    if ':' in line and line.strip() != 'পিতা:':
                        data["father_name"] = line.split(':', 1)[1].strip()
                        field_status["father_name"] = True
                    elif i+1 < len(lines):
                        data["father_name"] = lines[i+1].strip()
                        field_status["father_name"] = True
                    break
        
        # ---- 5. Mother name ----
        mother_match = re.search(r'মাতা:\s*([^\n]+)', text, re.IGNORECASE)
        if mother_match:
            data["mother_name"] = mother_match.group(1).strip()
            field_status["mother_name"] = True
        
        # ---- 6. Occupation ----
        occ_match = re.search(r'পেশা:\s*(.+?)(?=\s*(?:জন্ম|তারিখ|ঠিকানা:|ঠিকান:|$))', text, re.IGNORECASE | re.DOTALL)
        if occ_match:
            occ = occ_match.group(1).strip()
            occ = re.split(r'(জন্ম|তারিখ)', occ)[0].strip()
            data["occupation"] = occ.rstrip(',')
            if data["occupation"]:
                field_status["occupation"] = True
        
        # ---- 7. Date of birth ----
        dob_match = re.search(r'(?:জন্ম\s*)?তারিখ:\s*([^\n]+?)(?=\s*(?:ঠিকানা:|ঠিকান:|$))', text, re.IGNORECASE | re.DOTALL)
        if not dob_match:
            dob_match = re.search(r'জন্ম\s*\n\s*তারিখ:\s*([^\n]+)', text, re.IGNORECASE)
        if dob_match:
            raw_date = dob_match.group(1).strip()
            raw_date = re.sub(r'[,\s]+$', '', raw_date)
            data["date_of_birth_bangla"] = raw_date
            field_status["date_of_birth_bangla"] = True
            
            # Convert to English digits and clean
            eng_date = raw_date.translate(bn2en)
            eng_date = re.sub(r'[^0-9/]', '', eng_date)
            
            if eng_date:
                try:
                    parts = eng_date.split('/')
                    if len(parts) == 3:
                        d, m, y = parts
                        if len(y) == 2:
                            yy = int(y)
                            y = f"19{yy}" if yy >= 70 else f"20{yy}"
                        dt = datetime.strptime(f"{d}/{m}/{y}", "%d/%m/%Y")
                        data["date_of_birth_eng"] = dt.strftime("%Y-%m-%d")
                        field_status["date_of_birth_eng"] = True
                    else:
                        data["date_of_birth_eng"] = ""
                except Exception:
                    data["date_of_birth_eng"] = ""
            else:
                data["date_of_birth_eng"] = ""
        
        # ---- 8. Address (handles both "ঠিকানা:" and misspelled "ঠিকান:") ----
        # Try multiple patterns
        addr_match = re.search(r'ঠিকানা:\s*(.+)$', text, re.IGNORECASE | re.DOTALL)
        if not addr_match:
            # Try with common misspelling (missing 'া')
            addr_match = re.search(r'ঠিকান:\s*(.+)$', text, re.IGNORECASE | re.DOTALL)
        if not addr_match:
            # Try pattern that captures until end of text
            addr_match = re.search(r'ঠিকান[া]?:\s*(.+)$', text, re.IGNORECASE | re.DOTALL)
        
        if addr_match:
            addr = addr_match.group(1).strip()
            # Replace newlines with spaces
            addr = re.sub(r'\s+', ' ', addr)
            # Remove trailing commas and spaces
            addr = re.sub(r'[,\s]+$', '', addr)
            data["address"] = addr
            if addr:
                field_status["address"] = True
        else:
            # Fallback: line-by-line capture
            lines = text.split('\n')
            addr_parts = []
            capture = False
            # Also check for misspelled version
            for line in lines:
                if 'ঠিকানা:' in line or 'ঠিকান:' in line:
                    capture = True
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            addr_parts.append(parts[1].strip())
                        else:
                            addr_parts.append(line.strip())
                    else:
                        addr_parts.append(line.strip())
                elif capture and not any(key in line for key in ['নাম:', 'ভোটার নং:', 'পিতা:', 'মাতা:', 'পেশা:', 'জন্ম', 'তারিখ:']):
                    addr_parts.append(line.strip())
                elif capture and any(key in line for key in ['নাম:', 'ভোটার নং:', 'পিতা:', 'มাতা:', 'পেশা:', 'জন্ম', 'তারিখ:']):
                    break
            if addr_parts:
                data["address"] = ' '.join(addr_parts).strip()
                if data["address"]:
                    field_status["address"] = True
        
        # Clean up address
        if data["address"]:
            data["address"] = re.sub(r',+', ',', data["address"]).strip(', ')
        
        # ---- Calculate overall status (true if ALL fields have data) ----
        all_fields_have_data = all(field_status.values())
        
        # ---- Add status and fields to the output ----
        data["status"] = all_fields_have_data
        data["fields"] = field_status
        
        return data

    def process(self) -> List[Dict]:
        """Main processing pipeline with grid visualization"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Started processing PDF: {self.pdf_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Debug images will be saved to: {self.debug_dir}")
        
        image_paths = self.pdf_to_images(dpi=200)
        total_pages = len(image_paths)
        
        all_voters = []
        
        for idx, img_path in enumerate(image_paths):
            page_num = idx + 1
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========== Page {page_num}/{total_pages} ==========")
            
            # Detect grid cells with visualization
            cells = self.detect_grid_cells(img_path, page_num)
            
            if not cells:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No cells detected, processing entire page...")
                text = self.extract_cell_text(img_path, (0, 0, 10000, 10000))
                if text:
                    cards = re.split(r'(?=\d{1,3}[\.\s]*নাম:)', text)
                    for card_text in cards:
                        if len(card_text.strip()) > 50:
                            voter_data = self.parse_voter_card(card_text)
                            if voter_data.get("name") or voter_data.get("voter_no"):
                                voter_data["_source_page"] = page_num
                                all_voters.append(voter_data)
            else:
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
                    else:
                        print(f"[DEBUG] Cell {cell_idx+1}: No valid text (length: {len(cell_text) if cell_text else 0})")
                
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Extracted {len(page_voters)} voters from page {page_num}")
                all_voters.extend(page_voters)
        
        # Save results
        out_path = os.path.join(self.output_dir, "voters.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_voters, f, ensure_ascii=False, indent=2)
        
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========== FINISHED ==========")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Total voters extracted: {len(all_voters)}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Output saved to: {out_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Debug grids saved to: {self.debug_dir}")
        
        return all_voters