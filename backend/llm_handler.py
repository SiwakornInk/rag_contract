import os
import re
from openai import OpenAI
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class LLMHandler:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url="https://api.deepseek.com"
        )
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Dict:
        page_match = re.search(r'หน้า\s*(\d+)|page\s*(\d+)', query.lower())

        if page_match and not context_chunks:
            page_number = page_match.group(1) or page_match.group(2)
            return {
                'answer': f"ไม่พบข้อมูลในหน้า {page_number} ของเอกสารที่เลือก อาจเป็นเพราะ:\n\n"
                         f"1. เอกสารมีจำนวนหน้าน้อยกว่า {page_number} หน้า\n"
                         f"2. หน้า {page_number} เป็นหน้าว่างหรือมีแต่รูปภาพ\n"
                         f"3. เกิดข้อผิดพลาดในการประมวลผลหน้านี้\n\n"
                         f"กรุณาตรวจสอบหมายเลขหน้าอีกครั้ง",
                'sources': []
            }

        context = self._format_context(context_chunks)

        system_prompt = """คุณเป็นผู้ช่วยวิเคราะห์สัญญาและเอกสารทางกฎหมาย
        ตอบคำถามโดยอ้างอิงจากข้อมูลที่ให้มาเท่านั้น 
        ระบุแหล่งอ้างอิง (ชื่อไฟล์และหน้า) ทุกครั้ง
        หากไม่มีข้อมูลเพียงพอ ให้แจ้งว่าไม่พบข้อมูล

        เน้นการตอบคำถามเกี่ยวกับ:
        - ระยะเวลาสัญญา วันเริ่มต้น วันสิ้นสุด
        - มูลค่าสัญญา ค่าจ้าง ค่าปรับ
        - คู่สัญญา ผู้ว่าจ้าง ผู้รับจ้าง
        - เงื่อนไข ข้อกำหนด ข้อตกลง
        - การชำระเงิน การส่งมอบ การรับประกัน
        
        สำหรับคำถามเกี่ยวกับหน้าเฉพาะเจาะจง ให้แสดงเนื้อหาทั้งหมดในหน้านั้นอย่างละเอียด"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nคำถาม: {query}"}
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.15,
            max_tokens=3500
        )

        answer = response.choices[0].message.content

        return {
            'answer': answer,
            'sources': self._extract_sources(context_chunks)
        }
    
    def generate_document_title(self, document_info: Dict) -> str:
        doc_type = document_info.get('document_type', 'document')
        language = document_info.get('language', 'unknown')

        if doc_type == 'contract':
            prefix = "สัญญา: "
        else:
            prefix = "เอกสาร: "

        prompt = f"""วิเคราะห์เอกสารและสร้างชื่อที่สื่อความหมายชัดเจน

            ข้อมูลเอกสาร:
            - ชื่อไฟล์: {document_info.get('filename', '')}
            - ประเภท: {doc_type}
            - ภาษา: {language}
            - จำนวนหน้า: {document_info.get('total_pages', 0)}
            - ชื่อเดิม: {document_info.get('original_title', '')[:200]}
            - บทคัดย่อ: {document_info.get('abstract', '')[:500]}
            - ตัวอย่างเนื้อหา: {document_info.get('sample_text', '')[:1000]}

            หลักการสร้างชื่อสำหรับสัญญา:
            1. ความยาวไม่เกิน 80 ตัวอักษร
            2. ระบุประเภทสัญญาให้ชัดเจน (เช่น จ้างเหมา ซื้อขาย เช่า บริการ)
            3. ระบุคู่สัญญาหรือหน่วยงานหากมีข้อมูล
            4. ระบุปีหรือช่วงเวลาหากมี
            5. ใช้ภาษาที่ถูกต้องตามหลักไวยากรณ์
            6. ตัวอย่าง: "สัญญาจ้างเหมาก่อสร้าง - บริษัท ABC กับ XYZ (2567)"

            ข้อควรระวัง:
            - อย่าย่อคำจนผิดความหมาย
            - คงไว้ซึ่งคำศัพท์เฉพาะทางที่สำคัญ
            - ใช้ภาษาที่เหมาะสมกับประเภทเอกสาร

            ตอบเป็นชื่อเดียวเท่านั้น ไม่ต้องมีคำอธิบายเพิ่มเติม"""

        messages = [
            {"role": "system", "content": "สร้างชื่อที่สื่อความหมายชัดเจนโดยใช้ข้อมูลที่ให้มา รักษาความถูกต้องของภาษาและไวยากรณ์"},
            {"role": "user", "content": prompt}
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.15,
            max_tokens=200
        )

        title = response.choices[0].message.content.strip()

        title = re.sub(r'^["\'](.*)["\']$', r'\1', title)
        title = title.replace('"', '').replace("'", '')

        if title.startswith("สัญญา:") or title.startswith("เอกสาร:"):
            title = title.split(":", 1)[1].strip()

        full_title = prefix + title

        if len(full_title) > 150:
            full_title = full_title[:147] + "..."

        return full_title
    
    def _format_context(self, chunks: List[Dict]) -> str:
        context_parts = []

        for i, chunk in enumerate(chunks):
            if chunk.get('source') == 'sql' and 'total_pages' in chunk.get('metadata', {}):
                source = f"[{chunk['filename']} - รวม {chunk['metadata']['total_pages']} หน้า]"
            else:
                source = f"[{chunk['filename']} - หน้า {chunk['page']}]"

            context_parts.append(f"{source}\n{chunk['text']}\n")

        return "\n---\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        sources = []
        seen = set()
        
        for chunk in chunks:
            key = f"{chunk['filename']}-{chunk['page']}"
            if key not in seen:
                seen.add(key)
                sources.append({
                    'filename': chunk['filename'],
                    'page': chunk['page'],
                    'title': chunk['title']
                })
        
        return sources