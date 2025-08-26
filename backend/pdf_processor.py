import pdfplumber
import pytesseract
from PIL import Image
import io
import re
from typing import List, Dict, Tuple, Optional, Any
from google.cloud import vision
import os
import json
import base64
from collections import Counter
import numpy as np
import easyocr

class PDFProcessor:
    def __init__(self):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'googlecloudvisionservice.json'
        self.vision_client = vision.ImageAnnotatorClient()
        self.easyocr_reader = None
        self.chunk_size = 1500
        self.chunk_overlap = 300
        self.min_chunk_size = 100
        self.use_ocr_for_images = True
        self.use_ocr_for_failed_text = True
        
    def _init_easyocr(self):
        if self.easyocr_reader is None:
            print("Initializing EasyOCR (Thai + English)...")
            try:
                import torch
                gpu_available = torch.cuda.is_available()
            except ImportError:
                gpu_available = False
            
            self.easyocr_reader = easyocr.Reader(['th', 'en'], gpu=gpu_available, verbose=False)
            print(f"EasyOCR initialized successfully (GPU: {gpu_available})")
        
    def extract_pdf_content(self, pdf_path: str, use_cloud_ocr: bool = True) -> Dict:
        document_data = {
            'title': '',
            'abstract': '',
            'chunks': [],
            'total_pages': 0,
            'document_type': 'unknown',
            'metadata': {},
            'full_text_sample': '',
            'extraction_stats': {
                'total_pages': 0,
                'pages_with_text': 0,
                'pages_ocr_used': 0,
                'pages_failed': 0,
                'failed_pages': []
            }
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            document_data['total_pages'] = len(pdf.pages)
            document_data['extraction_stats']['total_pages'] = len(pdf.pages)
            
            all_text = []
            all_chunks = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ''
                page_had_content = False
                
                if page_text.strip():
                    page_had_content = True
                    document_data['extraction_stats']['pages_with_text'] += 1
                elif self.use_ocr_for_failed_text:
                    print(f"Page {page_num}: No text found, attempting OCR...")
                    if use_cloud_ocr:
                        page_text = self._ocr_full_page_cloud(page)
                    else:
                        page_text = self._ocr_full_page_local(page)
                    
                    if page_text.strip():
                        page_had_content = True
                        document_data['extraction_stats']['pages_ocr_used'] += 1
                    else:
                        document_data['extraction_stats']['pages_failed'] += 1
                        document_data['extraction_stats']['failed_pages'].append(page_num)
                        print(f"Page {page_num}: OCR failed to extract text")
                
                all_text.append(page_text)
                
                chunks = self._create_chunks_from_page(page_text, page_num)
                all_chunks.extend(chunks)
                
                tables = page.extract_tables()
                for table in tables:
                    if table and self._is_valid_table(table):
                        table_text = self._table_to_text(table)
                        all_chunks.append({
                            'text': table_text,
                            'type': 'table',
                            'page': page_num,
                            'metadata': {}
                        })
                        page_had_content = True
                
                if self.use_ocr_for_images:
                    try:
                        images = page.images
                        for img_idx, img in enumerate(images[:5]):
                            try:
                                if use_cloud_ocr:
                                    img_data = self._process_image_cloud(page, img, img_idx)
                                else:
                                    img_data = self._process_image_local(page, img, img_idx)
                                    
                                if img_data and img_data['text']:
                                    all_chunks.append({
                                        'text': f"รูปภาพ: {img_data['text']}",
                                        'type': 'image',
                                        'page': page_num,
                                        'metadata': {'image_type': img_data['type']}
                                    })
                                    page_had_content = True
                            except Exception as e:
                                print(f"Image processing error: {e}")
                    except Exception as e:
                        print(f"Image extraction error on page {page_num}: {e}")
                
                if not page_had_content and page_num not in document_data['extraction_stats']['failed_pages']:
                    document_data['extraction_stats']['pages_failed'] += 1
                    document_data['extraction_stats']['failed_pages'].append(page_num)
            
            document_data['title'] = self._extract_title(all_text[:5])
            document_data['abstract'] = self._extract_abstract(all_text)
            document_data['chunks'] = all_chunks
            document_data['full_text_sample'] = ' '.join(all_text[:3])[:1000]
            document_data['document_type'] = self._classify_document_type(all_text)
            document_data['metadata']['language'] = self._detect_language(all_text[:5])
            
        return document_data
    
    def _ocr_full_page_cloud(self, page) -> str:
        try:
            import time
            start_time = time.time()
            
            img = page.to_image(resolution=200)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            image = vision.Image(content=img_buffer.read())
            
            # เพิ่ม timeout 30 วินาที
            from google.api_core.client_options import ClientOptions
            from google.api_core.timeout import TimeoutToDeadlineTimeout
            
            response = self.vision_client.text_detection(
                image=image, 
                timeout=30
            )
            
            elapsed = time.time() - start_time
            print(f"Cloud OCR completed in {elapsed:.2f} seconds")
            
            if response.text_annotations:
                return response.text_annotations[0].description
            return ""
        except Exception as e:
            print(f"Cloud OCR error (will return empty): {e}")
            return ""
    
    def _preprocess_image_for_ocr(self, img_array: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        from PIL import Image, ImageEnhance, ImageFilter
        import cv2
        
        # Convert to PIL
        img_pil = Image.fromarray(img_array)
        
        # Convert to grayscale if needed
        if img_pil.mode != 'L':
            img_pil = img_pil.convert('L')
        
        # เพิ่ม contrast
        enhancer = ImageEnhance.Contrast(img_pil)
        img_pil = enhancer.enhance(2.0)
        
        # เพิ่ม sharpness
        enhancer = ImageEnhance.Sharpness(img_pil)
        img_pil = enhancer.enhance(2.0)
        
        # Convert back to numpy
        img_array = np.array(img_pil)
        
        # Apply threshold for better text clarity
        _, img_array = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return img_array
    
    def _ocr_full_page_local(self, page) -> str:
        try:
            self._init_easyocr()
            
            img = page.to_image(resolution=200)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            
            img_pil = Image.open(img_buffer)
            img_array = np.array(img_pil)
            
            # Preprocess image for better OCR
            img_array = self._preprocess_image_for_ocr(img_array)
            
            result = self.easyocr_reader.readtext(img_array, detail=0, paragraph=True, width_ths=0.7, height_ths=0.7)
            
            return '\n'.join(result)
        except Exception as e:
            print(f"Local OCR error: {e}")
            return ""
    
    def _process_image_cloud(self, page, img_obj, img_idx: int) -> Optional[Dict]:
        try:
            if isinstance(img_obj, dict) and 'x0' in img_obj and 'top' in img_obj:
                bbox = (img_obj['x0'], img_obj['top'], img_obj['x1'], img_obj['bottom'])
            elif isinstance(img_obj, dict) and 'bbox' in img_obj:
                bbox = img_obj['bbox']
            else:
                return None
            
            try:
                bbox = tuple(float(x) if x is not None else 0 for x in bbox)
                page_width = float(page.width)
                page_height = float(page.height)
            except (TypeError, ValueError) as e:
                print(f"Invalid bbox or page dimensions: {e}")
                return None
            
            if any(x < 0 or x > max(page_width, page_height) * 2 for x in bbox):
                print(f"Skipping image with invalid bbox: {bbox}")
                return None
            
            safe_bbox = (
                max(0, min(bbox[0], page_width - 1)),
                max(0, min(bbox[1], page_height - 1)),
                max(1, min(bbox[2], page_width)),
                max(1, min(bbox[3], page_height))
            )
            
            if safe_bbox[2] - safe_bbox[0] < 1 or safe_bbox[3] - safe_bbox[1] < 1:
                print(f"Bbox too small after clipping: {safe_bbox}")
                return None
            
            try:
                img = page.within_bbox(safe_bbox).to_image(resolution=200)
            except Exception as e:
                print(f"Failed to extract image with safe_bbox {safe_bbox}: {e}")
                return None
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            image = vision.Image(content=img_buffer.read())
            
            # Text detection with timeout
            text_response = self.vision_client.text_detection(
                image=image, 
                timeout=30
            )
            text_content = ""
            if text_response.text_annotations:
                text_content = text_response.text_annotations[0].description
            
            # Label detection with timeout
            label_response = self.vision_client.label_detection(
                image=image, 
                timeout=30
            )
            labels = [label.description for label in label_response.label_annotations[:5]]
            
            return {
                'index': img_idx,
                'text': text_content,
                'labels': labels,
                'type': self._classify_image_type(labels, text_content)
            }
            
        except Exception as e:
            print(f"Cloud image processing error: {e}")
            return None
    
    def _process_image_local(self, page, img_obj, img_idx: int) -> Optional[Dict]:
        try:
            self._init_easyocr()
            
            if isinstance(img_obj, dict) and 'x0' in img_obj and 'top' in img_obj:
                bbox = (img_obj['x0'], img_obj['top'], img_obj['x1'], img_obj['bottom'])
            elif isinstance(img_obj, dict) and 'bbox' in img_obj:
                bbox = img_obj['bbox']
            else:
                return None
            
            try:
                bbox = tuple(float(x) if x is not None else 0 for x in bbox)
                page_width = float(page.width)
                page_height = float(page.height)
            except (TypeError, ValueError) as e:
                print(f"Invalid bbox or page dimensions: {e}")
                return None
            
            if any(x < 0 or x > max(page_width, page_height) * 2 for x in bbox):
                print(f"Skipping image with invalid bbox: {bbox}")
                return None
            
            safe_bbox = (
                max(0, min(bbox[0], page_width - 1)),
                max(0, min(bbox[1], page_height - 1)),
                max(1, min(bbox[2], page_width)),
                max(1, min(bbox[3], page_height))
            )
            
            if safe_bbox[2] - safe_bbox[0] < 1 or safe_bbox[3] - safe_bbox[1] < 1:
                print(f"Bbox too small after clipping: {safe_bbox}")
                return None
            
            try:
                img = page.within_bbox(safe_bbox).to_image(resolution=200)
            except Exception as e:
                print(f"Failed to extract image with safe_bbox {safe_bbox}: {e}")
                return None
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            
            img_pil = Image.open(img_buffer)
            img_array = np.array(img_pil)
            
            # Preprocess image for better OCR
            img_array = self._preprocess_image_for_ocr(img_array)
            
            result = self.easyocr_reader.readtext(img_array, detail=0, paragraph=True, width_ths=0.7, height_ths=0.7)
            text_content = '\n'.join(result)
            
            return {
                'index': img_idx,
                'text': text_content,
                'labels': [],
                'type': self._classify_image_type_by_text(text_content)
            }
            
        except Exception as e:
            print(f"Local image processing error: {e}")
            return None
    
    def _classify_image_type_by_text(self, text_content: str) -> str:
        text_lower = text_content.lower()
        
        if any(word in text_lower for word in ['ตาราง', 'table', 'รายการ', 'list']):
            return 'table_image'
        elif any(word in text_lower for word in ['สูตร', 'formula', 'equation', '=']):
            return 'equation'
        elif len(text_content) > 50:
            return 'text_heavy'
        else:
            return 'general'
    
    def _is_valid_table(self, table: List[List]) -> bool:
        if not table or len(table) < 2:
            return False
        
        non_empty_cells = sum(1 for row in table for cell in row if cell and str(cell).strip())
        total_cells = len(table) * len(table[0]) if table[0] else 0
        
        if total_cells == 0:
            return False
            
        fill_rate = non_empty_cells / total_cells
        return fill_rate > 0.2
    
    def _table_to_text(self, table: List[List]) -> str:
        if not table:
            return ""
        
        text_parts = ["ตารางข้อมูล:"]
        
        for row in table:
            row_text = " | ".join(str(cell) if cell else "-" for cell in row)
            if row_text.replace("|", "").replace("-", "").strip():
                text_parts.append(row_text)
        
        return "\n".join(text_parts)
    
    def _classify_image_type(self, labels: List[str], text_content: str) -> str:
        label_text = ' '.join(labels).lower()
        
        if any(word in label_text for word in ['chart', 'graph', 'plot', 'diagram']):
            return 'diagram'
        elif any(word in label_text for word in ['table', 'spreadsheet']):
            return 'table_image'
        elif any(word in label_text for word in ['equation', 'formula', 'mathematical']):
            return 'equation'
        elif text_content and len(text_content) > 50:
            return 'text_heavy'
        elif any(word in label_text for word in ['logo', 'icon', 'symbol']):
            return 'logo'
        else:
            return 'general'
    
    def _detect_language(self, text_samples: List[str]) -> str:
        combined_text = ' '.join(text_samples)
        
        thai_chars = len(re.findall(r'[ก-๙]', combined_text))
        english_chars = len(re.findall(r'[a-zA-Z]', combined_text))
        total_chars = len(re.findall(r'[ก-๙a-zA-Z]', combined_text))
        
        if total_chars == 0:
            return 'unknown'
        
        thai_ratio = thai_chars / total_chars
        english_ratio = english_chars / total_chars
        
        if thai_ratio > 0.6:
            return 'thai'
        elif english_ratio > 0.6:
            return 'english'
        else:
            return 'mixed'
    
    def _classify_document_type(self, all_text: List[str]) -> str:
        first_pages = ' '.join(all_text[:5]).lower()
        
        contract_indicators = [
            'สัญญา', 'contract', 'agreement',
            'คู่สัญญา', 'parties',
            'ข้อตกลง', 'terms',
            'ผู้ว่าจ้าง', 'ผู้รับจ้าง', 'employer', 'contractor',
            'ข้อกำหนด', 'conditions',
            'ลงนาม', 'signature'
        ]
        
        indicator_count = sum(1 for indicator in contract_indicators if indicator in first_pages)
        
        if indicator_count >= 2:
            return 'contract'
        
        return 'document'
    
    def _extract_title(self, first_pages: List[str]) -> str:
        for page_text in first_pages:
            lines = page_text.split('\n')
            for line in lines[:20]:
                line = line.strip()
                if 20 <= len(line) <= 200 and not any(skip in line.lower() for skip in ['โดย', 'by', 'หน้า', 'page']):
                    return line
        return "Untitled Document"
    
    def _extract_abstract(self, all_text: List[str]) -> str:
        for i, page_text in enumerate(all_text[:20]):
            if any(marker in page_text.lower() for marker in ['บทคัดย่อ', 'abstract', 'สรุป', 'summary']):
                lines = page_text.split('\n')
                abstract_lines = []
                start_collecting = False
                
                for line in lines:
                    if any(marker in line.lower() for marker in ['บทคัดย่อ', 'abstract', 'สรุป', 'summary']):
                        start_collecting = True
                        continue
                    
                    if start_collecting and line.strip():
                        if any(end in line.lower() for end in ['คำสำคัญ', 'keywords', 'บทที่', 'chapter', 'ข้อ', 'clause']):
                            break
                        abstract_lines.append(line.strip())
                
                if abstract_lines:
                    return ' '.join(abstract_lines)[:1000]
        
        return ""
    
    def _create_chunks_from_page(self, text: str, page_num: int) -> List[Dict]:
        if not text.strip():
            return []
        
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'type': 'text',
                        'page': page_num,
                        'metadata': {}
                    })
                
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + sentence + " "
        
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append({
                'text': current_chunk.strip(),
                'type': 'text',
                'page': page_num,
                'metadata': {}
            })
        
        return chunks