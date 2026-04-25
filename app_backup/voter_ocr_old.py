# file: app/voter_ocr.py

import os
import re
import cv2
import json
import numpy as np
from datetime import datetime
from typing import List, Dict
from pdf2image import convert_from_path
import easyocr

class VoterOCRProcessor:
    def __init__(self, pdf_path: str, output_dir: str):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.poppler_path = None

        # Initialize EasyOCR with Bangla and English support
        self.ocr = easyocr.Reader(['bn', 'en'], gpu=False)

    def pdf_to_images(self, dpi: int = 300) -> List[str]:
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            fmt='png',
            poppler_path=self.poppler_path
        )

        paths = []
        for i, img in enumerate(images):
            p = os.path.join(self.output_dir, f"page_{i}.png")
            img.save(p)
            paths.append(p)

        return paths

    def process(self) -> List[Dict]:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Started processing PDF: {self.pdf_path}")
        image_paths = self.pdf_to_images()
        total_pages = len(image_paths)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Converted PDF to {total_pages} images.")
        
        all_voters = []

        for idx, path in enumerate(image_paths):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing page {idx + 1}/{total_pages}...")
            img = cv2.imread(path)
            
            # Use EasyOCR to get all text lines and bounding boxes
            result = self.ocr.readtext(img)
            if not result:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No text found on page {idx + 1}.")
                continue
                
            lines = result
            
            # Sort lines by their top-left Y coordinate
            lines.sort(key=lambda x: x[0][0][1])

            # Grouping logic: Voter cards usually have a consistent height
            current_group = []
            grouped_texts = []
            
            last_y_bottom = -1
            threshold = 50 # Adjust based on image resolution

            for line in lines:
                bbox = line[0]
                text = line[1]
                
                # Top-left and Bottom-left Y coordinates
                y_top = bbox[0][1]
                y_bottom = bbox[3][1]
                
                # If this block is far below the previous group, start a new card
                if last_y_bottom != -1 and y_top > last_y_bottom + threshold:
                    if current_group:
                        grouped_texts.append("\n".join(current_group))
                        current_group = []
                
                current_group.append(text)
                last_y_bottom = max(last_y_bottom, y_bottom)

            if current_group:
                grouped_texts.append("\n".join(current_group))

            page_voters = 0
            for text in grouped_texts:
                voters = self.parse_voters(text)
                all_voters.extend(voters)
                page_voters += len(voters)
                
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Extracted {page_voters} voter cards from page {idx + 1}.")

        out_path = os.path.join(self.output_dir, "voters.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_voters, f, ensure_ascii=False, indent=2)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Finished processing. Total voter cards extracted: {len(all_voters)}.")
        return all_voters

    def parse_voters(self, text: str) -> List[Dict]:
        voters = []
        bn2en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

        # Split by potential voter card starts (e.g., SL number followed by Name)
        blocks = re.split(r"(?=\d{1,3}[\.]?\s*নাম:)", text)

        for block in blocks:
            if not block.strip():
                continue
                
            data = {}

            def find(p):
                m = re.search(p, block)
                return m.group(1).strip() if m else ""

            data["sl"] = find(r"(\d{1,3})[\.]?\s*নাম:")
            data["name"] = find(r"নাম:\s*([^\n]+)")
            data["voter_no"] = find(r"ভোটার নং:\s*([০-৯]+)")
            data["father_name"] = find(r"(?:পিতা|স্বামী):\s*([^\n]+)")
            data["mother_name"] = find(r"মাতা:\s*([^\n]+)")
            data["occupation"] = find(r"পেশা:\s*([^\n,]+)")
            data["date_of_birth_bangla"] = find(r"তারিখ:\s*([০-৯/]+)")
            data["address"] = find(r"ঠিকানা:\s*([^\n]+)")

            if data["date_of_birth_bangla"]:
                en = data["date_of_birth_bangla"].translate(bn2en)
                data["date_of_birth_eng"] = self.convert_date(en)

            if data["name"] or data["voter_no"]:
                voters.append(data)

        return voters

    def convert_date(self, d: str) -> str:
        # replace multiple spaces, dashes, dots with a single slash
        d = re.sub(r'[\s\-\.]+', '/', d.strip())
        d = d.strip('/')
        try:
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            try:
                # Fallback for year only or other formats
                return datetime.strptime(d, "%Y/%m/%d").strftime("%Y-%m-%d")
            except:
                return d # Return as is if parsing fails
