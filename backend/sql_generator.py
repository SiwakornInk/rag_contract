from typing import Dict, List, Optional
import re
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

class SQLGenerator:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url="https://api.deepseek.com"
        )
        
        # แก้ไข schema ให้ตรงกับเวอร์ชันใหม่
        self.schema = """
        -- Current runtime schema (description column removed)
        CREATE TABLE documents (
            id NUMBER DEFAULT doc_seq.NEXTVAL PRIMARY KEY,
            file_name VARCHAR2(500) NOT NULL,
            name VARCHAR2(1000),
            page_count NUMBER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            properties JSON,
            file_data BLOB
        );

        CREATE TABLE content_segments (
            id NUMBER DEFAULT segment_seq.NEXTVAL PRIMARY KEY,
            document_id NUMBER NOT NULL,
            content CLOB NOT NULL,
            category VARCHAR2(50),
            page_ref NUMBER,
            sequence_num NUMBER,
            vector_data VECTOR(1024, FLOAT32),
            attributes JSON,
            CONSTRAINT fk_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """
        
        self.dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 
            'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE', 'EXECUTE',
            'EXEC', 'CALL', 'MERGE', 'REPLACE', 'SET', 'BEGIN',
            'COMMIT', 'ROLLBACK', 'SAVEPOINT'
        ]
    
    def generate_sql(self, query: str, doc_filename: Optional[str] = None) -> Dict:
        query_lower = query.lower()
        
        # Single page patterns - แก้ไขให้ใช้ชื่อ column ใหม่
        single_page_match = re.search(r'หน้า\s*(\d+)(?!\s*[-–ถึงและ])|page\s*(\d+)(?!\s*[-–to])', query_lower)
        if single_page_match:
            page_num = single_page_match.group(1) or single_page_match.group(2)
            sql = f'''SELECT c.content, c.page_ref, c.category, d.file_name, d.name 
                     FROM content_segments c 
                     JOIN documents d ON c.document_id = d.id 
                     WHERE c.page_ref = {page_num}'''
            
            if doc_filename:
                sql += ' AND d.file_name = :filename'
            
            sql += ' ORDER BY c.sequence_num FETCH FIRST 50 ROWS ONLY'
            
            return {
                'sql': sql,
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'content',
                'confidence': 0.95
            }
        
        # Multiple pages - แก้ไขให้ใช้ชื่อ column ใหม่
        multiple_pages = re.findall(r'\d+', query_lower)
        if len(multiple_pages) >= 2 and any(word in query_lower for word in ['หน้า', 'page']) and any(word in query_lower for word in ['และ', 'กับ', ',', 'and']):
            page_list = ','.join(multiple_pages)
            sql = f'''SELECT c.content, c.page_ref, c.category, d.file_name, d.name 
                     FROM content_segments c 
                     JOIN documents d ON c.document_id = d.id 
                     WHERE c.page_ref IN ({page_list})'''
            
            if doc_filename:
                sql += ' AND d.file_name = :filename'
            
            sql += ' ORDER BY c.page_ref, c.sequence_num FETCH FIRST 50 ROWS ONLY'
            
            return {
                'sql': sql,
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'content',
                'confidence': 0.95
            }
        
        # Page range patterns - แก้ไขให้ใช้ชื่อ column ใหม่
        page_match = re.search(r'หน้า\s*(\d+)\s*[-–ถึง]\s*(\d+)|page\s*(\d+)\s*[-–to]\s*(\d+)', query_lower)
        if page_match:
            start = page_match.group(1) or page_match.group(3)
            end = page_match.group(2) or page_match.group(4)
            sql = f'''SELECT c.content, c.page_ref, c.category, d.file_name, d.name 
                     FROM content_segments c 
                     JOIN documents d ON c.document_id = d.id 
                     WHERE c.page_ref BETWEEN {start} AND {end}'''
            
            if doc_filename:
                sql += ' AND d.file_name = :filename'
            
            sql += ' ORDER BY c.page_ref, c.sequence_num FETCH FIRST 50 ROWS ONLY'
            
            return {
                'sql': sql,
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'content',
                'confidence': 0.95
            }
        
        # Document count/pages queries - แก้ไขให้ใช้ชื่อ column ใหม่
        if any(word in query_lower for word in ['จำนวนหน้า', 'กี่หน้า', 'how many pages']):
            sql = 'SELECT d.name, d.file_name, d.page_count FROM documents d'
            conditions = []
            
            numbers = re.findall(r'\d+', query_lower)
            
            if ('มากกว่า' in query_lower or 'เกิน' in query_lower or 'more than' in query_lower) and numbers:
                conditions.append(f'd.page_count > {numbers[0]}')
            elif ('น้อยกว่า' in query_lower or 'ไม่เกิน' in query_lower or 'ต่ำกว่า' in query_lower or 'less than' in query_lower) and numbers:
                conditions.append(f'd.page_count < {numbers[0]}')
            elif ('เท่ากับ' in query_lower or 'equal' in query_lower) and numbers:
                conditions.append(f'd.page_count = {numbers[0]}')
            
            if doc_filename:
                conditions.append('d.file_name = :filename')
            
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            
            sql += ' ORDER BY d.page_count DESC FETCH FIRST 50 ROWS ONLY'
            
            return {
                'sql': sql,
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'metadata',
                'confidence': 0.9
            }
        
        # Table queries - แก้ไขให้ใช้ชื่อ column ใหม่
        if any(word in query_lower for word in ['ตาราง', 'table', 'กี่ตาราง']):
            sql = '''SELECT c.content, c.page_ref, d.file_name, d.name 
                    FROM content_segments c 
                    JOIN documents d ON c.document_id = d.id 
                    WHERE c.category = 'table' '''
            
            if doc_filename:
                sql += 'AND d.file_name = :filename '
            
            sql += 'ORDER BY c.page_ref FETCH FIRST 50 ROWS ONLY'
            
            return {
                'sql': sql,
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'content',
                'confidence': 0.8
            }
        
        # Use LLM for complex queries
        prompt = f"""You are a SQL expert for Oracle Database with Vector support.

SCHEMA:
{self.schema}

RULES:
1. ONLY generate SELECT statements - NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE
2. For numbers in WHERE clause, put the value directly (e.g., page_count > 100), NOT as parameter
3. Only use :filename parameter for file_name, nothing else  
4. For semantic search, use: VECTOR_DISTANCE(c.vector_data, :query_embedding, COSINE)
5. Always add FETCH FIRST 50 ROWS ONLY to limit results
6. Return format: {{"sql": "...", "needs_embedding": true/false, "embedding_terms": ["term1", "term2"], "query_type": "metadata|content|hybrid", "confidence": 0.0-1.0}}

USER QUERY: {query}
{f"SPECIFIC DOCUMENT: {doc_filename}" if doc_filename else "SEARCH ALL DOCUMENTS"}

Return ONLY the JSON object, no markdown, no code blocks, no explanations."""

        messages = [
            {"role": "system", "content": "You are a SQL expert. Generate only valid JSON responses without any markdown formatting."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            if '```json' in result_text:
                match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
                if match:
                    result_text = match.group(1)
            elif '```' in result_text:
                match = re.search(r'```\s*(.*?)\s*```', result_text, re.DOTALL)
                if match:
                    result_text = match.group(1)

            result_text = result_text.strip()
            if not result_text.startswith('{'):
                first_brace = result_text.find('{')
                last_brace = result_text.rfind('}')
                if first_brace != -1 and last_brace != -1:
                    result_text = result_text[first_brace:last_brace+1]

            result = json.loads(result_text)

            sql = result.get('sql', '')
            self._validate_sql(sql)

            result.setdefault('needs_embedding', False)
            result.setdefault('embedding_terms', [])
            result.setdefault('query_type', 'hybrid')
            result.setdefault('confidence', 0.5)

            return result

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {result_text}")
            
            return {
                'sql': 'SELECT d.name, d.file_name FROM documents d WHERE ROWNUM <= 10',
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'hybrid',
                'confidence': 0.0
            }
        except Exception as e:
            print(f"SQL generation error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'sql': 'SELECT d.name, d.file_name FROM documents d WHERE ROWNUM <= 10',
                'needs_embedding': False,
                'embedding_terms': [],
                'query_type': 'hybrid', 
                'confidence': 0.0
            }
    
    def _validate_sql(self, sql: str):
        sql_upper = sql.upper()
        
        for keyword in self.dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', sql_upper):
                raise ValueError(f"Dangerous operation detected: {keyword}")
        
        if not sql_upper.strip().startswith('SELECT'):
            raise ValueError("Only SELECT statements are allowed")
        
        if ';' in sql.strip()[:-1]:
            raise ValueError("Multiple statements not allowed")
        
        if 'FETCH FIRST' not in sql_upper and 'ROWNUM' not in sql_upper:
            raise ValueError("Query must include FETCH FIRST or ROWNUM to limit results")