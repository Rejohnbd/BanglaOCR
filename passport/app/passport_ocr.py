# passport-ocr/app/passport_ocr_fast.py
import os
import re
import json
import gc
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from pdf2image import convert_from_path
import easyocr
import warnings
warnings.filterwarnings("ignore")

print("[INFO] Loading Enhanced Passport OCR (English only) – Precise extraction")


class FastPassportOCRProcessor:
    def __init__(self, file_path: str, output_dir: str, file_type: str = "image"):
        self.file_path = file_path
        self.output_dir = output_dir
        self.file_type = file_type
        os.makedirs(output_dir, exist_ok=True)
        self.debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)

        print("[INIT] Initializing EasyOCR (English only)...")
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("[INIT] Ready")

    # ---------- Preprocessing (grayscale, CLAHE, denoise) ----------
    def preprocess_image(self, image_path: str) -> str:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.save_debug_image(gray, "1_grayscale.png", "Grayscale")
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        self.save_debug_image(enhanced, "2_clahe.png", "CLAHE contrast")
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
        self.save_debug_image(denoised, "3_denoised.png", "Denoised")
        temp_path = os.path.join(self.output_dir, "preprocessed_temp.jpg")
        cv2.imwrite(temp_path, denoised)
        return temp_path

    # ---------- Debug helpers ----------
    def save_debug_image(self, img, name, desc=""):
        if getattr(self, 'generate_debug', True) is False:
            return
        if img is not None:
            path = os.path.join(self.debug_dir, name)
            cv2.imwrite(path, img)
            print(f"[DEBUG] Saved: {path} - {desc}")

    def draw_boxes(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return None
        result = self.reader.readtext(image_path)
        for (bbox, text, conf) in result:
            pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [pts], True, (0, 255, 0), 2)
            cv2.putText(img, f"{text[:15]}", (int(bbox[0][0]), int(bbox[0][1])-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        return img

    def generate_debug_images(self, image_path, full_text):
        img_with_boxes = self.draw_boxes(image_path)
        self.save_debug_image(img_with_boxes, "4_boxes.png", "Text boxes")
        h, w = 800, 1200
        text_img = np.ones((h, w, 3), dtype=np.uint8) * 255
        y = 30
        for line in full_text.split('\n')[:40]:
            cv2.putText(text_img, line[:100], (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            y += 25
        self.save_debug_image(text_img, "5_extracted_text.png", "OCR output preview")

    # ---------- PDF to image (300 DPI) ----------
    def convert_to_image(self) -> str:
        if self.file_type == "pdf":
            print("[STEP 1] Converting PDF to image (300 DPI)...")
            images = convert_from_path(self.file_path, dpi=300, fmt='jpeg',
                                       thread_count=1, first_page=1, last_page=1)
            if images:
                img_path = os.path.join(self.output_dir, "page.jpg")
                images[0].save(img_path, quality=95)
                return img_path
            return None
        return self.file_path

    # ---------- Text extraction with preprocessing ----------
    def extract_text(self, image_path: str) -> str:
        print("[STEP 2] Extracting text with preprocessing...")
        processed_path = self.preprocess_image(image_path)
        result = self.reader.readtext(processed_path, detail=0, paragraph=False)
        if processed_path != image_path and os.path.exists(processed_path):
            os.remove(processed_path)
        full_text = "\n".join(result) if result else ""
        print(f"[STEP 2] Extracted {len(full_text)} characters")
        return full_text

    # ---------- MRZ extraction (used as ground truth) ----------
    def extract_mrz(self, text: str) -> Dict:
        print("[STEP 3] Extracting MRZ...")
        mrz = {
            "type": "",
            "mrz_line1": "", "mrz_line2": "", "passport_number": "", "country_code": "",
            "surname": "", "given_name": "", "nationality": "", "date_of_birth": "",
            "sex": "", "date_of_expiry": "", "personal_number": ""
        }
        lines = text.split('\n')
        line1 = line2 = ""
        for i, line in enumerate(lines):
            clean = line.replace(' ', '')
            if clean.startswith('P<') and len(clean) > 30:
                line1 = clean
                if i+1 < len(lines):
                    next_clean = lines[i+1].replace(' ', '')
                    if len(next_clean) > 30:
                        line2 = next_clean
            elif len(clean) > 35 and not clean.startswith('P<') and not line2:
                line2 = clean
        mrz["mrz_line1"] = line1
        mrz["mrz_line2"] = line2
        if line1:
            mrz["type"] = line1[0] if line1 else ""
        if line1 and line1.startswith('P<'):
            if len(line1) >= 5:
                mrz["country_code"] = line1[2:5]
            name_part = line1[5:]
            if '<<' in name_part:
                names = name_part.split('<<', 1)
                mrz["surname"] = names[0].replace('<', ' ').strip()
                mrz["given_name"] = names[1].replace('<', ' ').strip()
            else:
                mrz["surname"] = name_part.replace('<', ' ').strip()
        if line2 and len(line2) >= 44:
            mrz["passport_number"] = line2[0:9].replace('<', '')
            mrz["nationality"] = line2[15:18].replace('<', '')
            dob_raw = line2[18:24]
            if dob_raw and dob_raw != '<<<<<<':
                # Convert YYMMDD to "DD MMM YYYY" (e.g., 880201 -> 01 FEB 1988)
                try:
                    day = dob_raw[0:2]
                    month_num = int(dob_raw[2:4])
                    year = "19" + dob_raw[4:6] if int(dob_raw[4:6]) > 30 else "20" + dob_raw[4:6]
                    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
                    month_name = months[month_num - 1] if 1 <= month_num <= 12 else ""
                    if month_name:
                        mrz["date_of_birth"] = f"{day} {month_name} {year}"
                    else:
                        mrz["date_of_birth"] = f"{day}/{dob_raw[2:4]}/{year}"
                except:
                    mrz["date_of_birth"] = dob_raw
            mrz["sex"] = line2[24] if len(line2) > 24 and line2[24] != '<' else ""
            exp_raw = line2[25:31]
            if exp_raw and exp_raw != '<<<<<<':
                try:
                    day = exp_raw[0:2]
                    month_num = int(exp_raw[2:4])
                    year = "20" + exp_raw[4:6]
                    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
                    month_name = months[month_num - 1] if 1 <= month_num <= 12 else ""
                    if month_name:
                        mrz["date_of_expiry"] = f"{day} {month_name} {year}"
                    else:
                        mrz["date_of_expiry"] = f"{day}/{exp_raw[2:4]}/{year}"
                except:
                    mrz["date_of_expiry"] = exp_raw
            mrz["personal_number"] = line2[31:42].replace('<', '')
        print(f"[STEP 3] MRZ: passport={mrz.get('passport_number', '')}, given={mrz.get('given_name', '')}")
        return mrz

    # ---------- Personal data (exact lines after "PERSONAL DATA") ----------
    def extract_personal_data(self, text: str) -> Dict:
        print("[STEP 4] Extracting personal data...")
        lines = text.split('\n')
        data = {"name": "", "father_name": "", "mother_name": "", "spouse_name": "", "permanent_address": ""}
        start_idx = None
        for i, line in enumerate(lines):
            if "PERSONAL DATA" in line.upper():
                start_idx = i + 1
                break
        if start_idx is None:
            return data
        # Collect next non‑empty lines until a line containing "Address:" or "Emergency" or "PEOPLE"
        collected = []
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if "Address:" in line or "EMERGENCY" in line.upper() or "PEOPLE'S" in line.upper():
                break
            collected.append(line)
            i += 1
        # The first three lines should be name, father, mother (if present)
        if len(collected) >= 1:
            data["name"] = collected[0]
        if len(collected) >= 2:
            data["father_name"] = collected[1]
        if len(collected) >= 3:
            data["mother_name"] = collected[2]
            
        addr_parts = []
        addr_start = False
        for line in lines:
            if "Address:" in line:
                addr_start = True
                val = line.split(":", 1)[-1].strip()
                if val:
                    addr_parts.append(val)
                continue
            if addr_start:
                if "Emergency" in line or "EMERGENCY" in line.upper() or "PEOPLE'S" in line.upper():
                    break
                if line.strip():
                    addr_parts.append(line.strip())
        
        if addr_parts:
            data["permanent_address"] = ", ".join(addr_parts).strip()
            
        print(f"[STEP 4] Personal data: {data}")
        return data

    # ---------- Emergency contact (exact block after "Emergency Contact:") ----------
    def extract_emergency_contact(self, text: str) -> Dict:
        print("[STEP 5] Extracting emergency contact...")
        lines = text.split('\n')
        contact = {"name": "", "relationship": "", "address": "", "telephone_no": ""}
        start_idx = None
        for i, line in enumerate(lines):
            if "Emergency Contact:" in line or "EMERGENCY CONTACT" in line.upper():
                start_idx = i + 1
                break
        if start_idx is None:
            return contact
        # Gather lines until a blank line or reaching passport section
        collected = []
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if "PEOPLE'S" in line.upper() or "PASSPORT" in line.upper():
                break
            collected.append(line)
            i += 1
        # Parse collected lines: first is name, then "Relationship", then relationship value, then address lines, then phone
        if len(collected) > 0:
            contact["name"] = collected[0]
            
        rel_idx = -1
        for idx, line in enumerate(collected):
            if "Relationship" in line:
                rel_idx = idx
                if ':' in line:
                    rel = line.split(':', 1)[1].strip()
                    if rel:
                        contact["relationship"] = rel
                    elif idx + 1 < len(collected):
                        contact["relationship"] = collected[idx+1]
                elif idx + 1 < len(collected):
                    contact["relationship"] = collected[idx+1]
                break
                
        address_parts = []
        phone_found = False
        
        start_addr_idx = 1
        if rel_idx != -1:
            start_addr_idx = rel_idx + 1 if contact["relationship"] not in collected else rel_idx + 2
            
        for i in range(start_addr_idx, len(collected)):
            line = collected[i]
            if line == contact["relationship"] and i <= rel_idx + 1:
                continue
            phone_match = re.search(r'\+?\d[\d\s-]{8,}', line)
            if phone_match:
                contact["telephone_no"] = phone_match.group(0).strip()
                phone_found = True
                break
            address_parts.append(line)
            
        if address_parts:
            contact["address"] = ", ".join(address_parts).strip()

        print(f"[STEP 5] Emergency contact: {contact}")
        return contact

    # ---------- Passport details (combine MRZ and OCR text) ----------
    def extract_passport_details(self, text: str, mrz: Dict) -> Dict:
        print("[STEP 6] Extracting passport details...")
        details = {
            "type": mrz.get("type", ""),
            "country_code": mrz.get("country_code", ""),
            "passport_no": mrz.get("passport_number", ""),
            "surname": mrz.get("surname", ""),
            "given_name": mrz.get("given_name", ""),
            "nationality": "",
            "personal_no": mrz.get("personal_number", ""),
            "date_of_birth": mrz.get("date_of_birth", ""),
            "previous_passport_no": "",
            "sex": mrz.get("sex", ""),
            "place_of_birth": "",
            "date_of_issue": "",
            "issuing_authority": "",
            "date_of_expiry": mrz.get("date_of_expiry", "")
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Passport No
            if "Passport" in line and "Number" in line:
                for j in range(i+1, min(i+3, len(lines))):
                    match = re.search(r'[A-Z]\d{8,9}', lines[j])
                    if match:
                        details["passport_no"] = match.group(0)
                        break
            
            # Personal No
            if "Personal No" in line:
                for j in range(i+1, min(i+3, len(lines))):
                    match = re.search(r'\d{10,}', lines[j])
                    if match:
                        details["personal_no"] = match.group(0)
                        break
                        
            # Nationality fallback
            if "Nationality" in line and not details["nationality"]:
                match = re.search(r'Nationality\s*:?\s*([^\n]+)', line, re.I)
                if match:
                    details["nationality"] = match.group(1).strip()
                    
            # Place of Birth
            if "Place of Birth" in line:
                for j in range(i+1, min(i+3, len(lines))):
                    val = lines[j].strip()
                    if val and len(val) > 3 and not re.search(r'\d', val):
                        details["place_of_birth"] = val
                        break
                        
            # Surname
            if "Surname" in line or "USurame" in line or "urame" in line.lower():
                for j in range(i+1, min(i+3, len(lines))):
                    val = lines[j].strip()
                    if val and len(val) >= 2 and val.isupper() and "Name" not in val:
                        if not details["surname"]:
                            details["surname"] = val
                        break

            # Given Name
            if "Given Name" in line or "RnTGiven" in line or "iven Name" in line:
                for j in range(i+1, min(i+3, len(lines))):
                    val = lines[j].strip()
                    if val and len(val) >= 2 and val.isupper() and "Nationality" not in val:
                        if not details["given_name"]:
                            details["given_name"] = val
                        break
                        
            # Issuing Authority
            if "Authority" in line or "DipidharA" in line or "DIP/DHAKA" in line.upper():
                for j in range(max(0, i-2), min(i+3, len(lines))):
                    val = lines[j].upper().replace('"', '').replace("'", "")
                    if "DIP" in val or "DHAKA" in val or "DIPIDHARA" in val:
                        details["issuing_authority"] = "DIP/DHAKA"
                        break
            
            # Previous Passport
            if "Previous" in line:
                for j in range(i, min(i+4, len(lines))):
                    match = re.search(r'[A-Z]{2}\d{7}', lines[j])
                    if match:
                        details["previous_passport_no"] = match.group(0)
                        break
                        
            # Dates
            match_date = re.search(r'\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{4}\b', line, re.I)
            if match_date:
                date_val = match_date.group(0).upper()
                if "Birth" in lines[max(0, i-2)] or "Birth" in lines[max(0, i-1)]:
                    details["date_of_birth"] = date_val
                elif "Issue" in lines[max(0, i-2)] or "Issue" in lines[max(0, i-1)] or "ssue" in lines[max(0, i-1)]:
                    details["date_of_issue"] = date_val
                elif "Expiry" in lines[max(0, i-2)] or "Expiry" in lines[max(0, i-1)]:
                    details["date_of_expiry"] = date_val
        
        # Fallbacks for dates by searching whole text if missed
        if not details["date_of_birth"] or len(details["date_of_birth"]) < 6:
            match = re.search(r'\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(?:19|20)\d{2}\b', text[text.find("Birth"):text.find("Birth")+100], re.I)
            if match: details["date_of_birth"] = match.group(0).upper()
            
        if not details["date_of_issue"]:
            match = re.search(r'\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(?:19|20)\d{2}\b', text[text.find("Issue"):text.find("Issue")+100], re.I)
            if match: details["date_of_issue"] = match.group(0).upper()
            
        if not details["date_of_expiry"] or len(details["date_of_expiry"]) < 6:
            match = re.search(r'\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(?:19|20)\d{2}\b', text[text.find("Expiry"):text.find("Expiry")+100], re.I)
            if match: details["date_of_expiry"] = match.group(0).upper()

        if not details["nationality"]:
            if "BANGLADESHI" in text or "BANGLADESH" in text:
                details["nationality"] = "BANGLADESH"

        if details["given_name"]:
            details["given_name"] = re.sub(r'[K<]+', '', details["given_name"]).strip()
        if details["surname"]:
            details["surname"] = re.sub(r'[<]+', '', details["surname"]).strip()
            
        if details["sex"] == "1" or "M" in details["sex"]:
            details["sex"] = "M"
        elif details["sex"] == "2" or "F" in details["sex"]:
            details["sex"] = "F"
            
        print(f"[STEP 6] Passport details: {details}")
        return details

    # ---------- Main process ----------
    def process(self, generate_debug: bool = True) -> Dict:
        self.generate_debug = generate_debug
        start_time = datetime.now()
        print("\n" + "="*60)
        print("[PROCESS] Starting Enhanced Passport OCR")
        print("="*60)

        try:
            image_path = self.convert_to_image()
            if not image_path:
                return {"error": "Failed to convert file"}
            print("full text extraction started")
            full_text = self.extract_text(image_path)
            if not full_text:
                return {"error": "No text extracted"}
            print("full_text======", full_text)
            print("full text extraction ended")
            # Save raw text for debugging
            with open(os.path.join(self.output_dir, "raw_text.txt"), "w", encoding="utf-8") as f:
                f.write(full_text)
            print("raw text saved")
            mrz_data = self.extract_mrz(full_text)
            personal = self.extract_personal_data(full_text)
            emergency = self.extract_emergency_contact(full_text)
            passport_details = self.extract_passport_details(full_text, mrz_data)

            result = {
                "personal_data": personal,
                "emergency_contact": emergency,
                "passport_details": passport_details,
                "mrz": {
                    "mrz_line1": mrz_data.get("mrz_line1", ""),
                    "mrz_line2": mrz_data.get("mrz_line2", "")
                }
            }

            # Remove empty fields cleanup so that empty keys are returned
            # (Previously empty fields were being removed here)


            if generate_debug:
                self.generate_debug_images(image_path, full_text)

            out_path = os.path.join(self.output_dir, "passport_data.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n[PROCESS] Completed in {elapsed:.2f} seconds")
            return result

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}