from typing import List, Dict, Optional
import asyncio
import json
import re
from database import OracleVectorDB
from embeddings import EmbeddingGenerator
from retriever import DocumentRetriever
from sql_generator import SQLGenerator
from reranker import Reranker
import numpy as np

class HybridRetriever:
    def __init__(self, db: OracleVectorDB, embedder: EmbeddingGenerator):
        self.db = db
        self.embedder = embedder
        self.vector_retriever = DocumentRetriever(db, embedder)
        self.sql_generator = SQLGenerator()
        self.reranker = Reranker()
        self.use_sql_search = True
    
    async def retrieve(self, query: str, doc_filename: Optional[str] = None, 
                      top_k: int = 15) -> List[Dict]:
        query_intent = self._analyze_query_intent(query)
        print(f"Query intent: {query_intent}")

        if query_intent.get('needs_document_selection', False) and not doc_filename:
            return [{
                'text': 'กรุณาระบุเอกสารที่ต้องการ เนื่องจากระบบมีหลายเอกสาร',
                'type': 'system_message',
                'page': 0,
                'filename': '',
                'title': '',
                'score': 1.0,
                'metadata': {'message_type': 'require_document_selection'}
            }]

        needs_sql = self._needs_sql_search(query)
        print(f"Query: {query}")
        print(f"Needs SQL search: {needs_sql}")

        if not needs_sql:
            chunks = self.vector_retriever.retrieve(query, doc_filename, top_k)
            if query_intent.get('is_overview_query', False):
                chunks = self._apply_overview_boosting(chunks, query_intent)
            return chunks[:top_k]

        sql_result = await self._async_sql_search(query, doc_filename)
        sql_chunks = sql_result.get('chunks', [])
        sql_confidence = sql_result.get('confidence', 0.5)
        sql_query_type = sql_result.get('query_type', 'hybrid')

        if sql_confidence >= 0.9 and sql_query_type == 'metadata' and sql_chunks:
            print(f"Using SQL-only results due to high confidence ({sql_confidence})")
            if self.reranker:
                return self.reranker.rerank(
                    query, 
                    sql_chunks, 
                    top_k=top_k,
                    query_intent=query_intent
                )
            return sql_chunks[:top_k]

        vector_chunks = await self._async_vector_search(query, doc_filename, top_k)

        if sql_confidence >= 0.8 and sql_query_type == 'metadata':
            weights = {'vector': 0.2, 'sql': 0.8}
        elif sql_confidence <= 0.3 or sql_query_type == 'content':
            weights = {'vector': 0.8, 'sql': 0.2}
        elif query_intent['primary_focus'] == 'metadata':
            weights = {'vector': 0.3, 'sql': 0.7}
        elif query_intent['primary_focus'] == 'content':
            weights = {'vector': 0.7, 'sql': 0.3}
        elif query_intent['primary_focus'] == 'overview':
            weights = {'vector': 0.6, 'sql': 0.4}
        else:
            weights = {'vector': 0.5, 'sql': 0.5}

        print(f"Using weights: {weights}")

        merged_chunks = self._smart_merge(vector_chunks, sql_chunks, weights)

        if query_intent.get('is_overview_query', False):
            merged_chunks = self._apply_overview_boosting(merged_chunks, query_intent)

        if merged_chunks and self.reranker:
            merged_chunks = self.reranker.rerank(
                query, 
                merged_chunks, 
                top_k=top_k,
                query_intent=query_intent
            )

        return merged_chunks[:top_k]
    
    def _needs_sql_search(self, query: str) -> bool:
        sql_indicators = [
            'มากกว่า', 'น้อยกว่า', 'ระหว่าง', 'เท่ากับ', 'เกิน', 'ไม่เกิน', 'ต่ำกว่า', 'สูงกว่า',
            'จำนวนหน้า', 'กี่หน้า', 'อัพโหลดเมื่อ', 'วันที่', 'เดือน', 'ปี',
            'ประเภท', 'ทั้งหมด', 'นับ', 'เฉลี่ย', 'รวม', 'กี่ไฟล์', 'กี่เอกสาร', 'กี่บท', 'กี่ตาราง',
            'เนื้อหาหน้า', 'ขอเนื้อหา', 'ข้อมูลหน้า',
            'ตั้งแต่หน้า', 'ถึงหน้า', 'จากหน้า', 'ไปหน้า',
            'ตั้งแต่', 'ถึง', 'จาก', 'ไป',
            'more than', 'less than', 'between', 'equal', 'exceed', 'over', 'under',
            'pages', 'uploaded', 'date', 'month', 'year',
            'type', 'all', 'count', 'average', 'total', 'how many',
            'content of page', 'page content',
            'from page', 'to page', 'page range',
            '>', '<', '>=', '<=', '=',
            'ไฟล์ไหน', 'เอกสารไหน', 'วิทยานิพนธ์ไหน', 'which document', 'which file'
        ]

        query_lower = query.lower()
        
        page_patterns = [
            r'หน้า\s*\d+\s*[-–]\s*\d+',
            r'page\s*\d+\s*[-–]\s*\d+',
            r'ตั้งแต่หน้า\s*\d+\s*ถึง\s*\d+',
            r'จากหน้า\s*\d+\s*ถึง\s*\d+',
            r'หน้า\s*\d+\s*ถึง\s*\d+',
            r'from page\s*\d+\s*to\s*\d+',
        ]

        for pattern in page_patterns:
            if re.search(pattern, query_lower):
                return True

        if re.search(r'หน้า\s*\d+|page\s*\d+', query_lower):
            return True

        return any(indicator in query_lower for indicator in sql_indicators)
    
    async def _async_vector_search(self, query: str, doc_filename: Optional[str], 
                                   top_k: int) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.vector_retriever.retrieve,
            query, doc_filename, top_k * 2
        )
    
    async def _async_sql_search(self, query: str, 
                       doc_filename: Optional[str]) -> Dict:
        try:
            sql_result = self.sql_generator.generate_sql(query, doc_filename)
            sql = sql_result['sql']
            needs_embedding = sql_result.get('needs_embedding', False)
            embedding_terms = sql_result.get('embedding_terms', [])
            query_type = sql_result.get('query_type', 'hybrid')
            confidence = sql_result.get('confidence', 0.5)

            print(f"Generated SQL: {sql}")
            print(f"Query type: {query_type}, Confidence: {confidence}")

            params = {}
            if needs_embedding and embedding_terms:
                combined_text = ' '.join(embedding_terms)
                embedding = self.embedder.encode(combined_text)
                params['query_embedding'] = embedding

            if ':filename' in sql and not doc_filename:
                print("Warning: SQL expects filename but none provided, removing filename filter")
                sql = re.sub(r'WHERE\s+d\.filename\s*=\s*:filename\s+AND\s+', 'WHERE ', sql)
                sql = re.sub(r'AND\s+d\.filename\s*=\s*:filename', '', sql)
                sql = re.sub(r'd\.filename\s*=\s*:filename\s+AND\s+', '', sql)
                sql = re.sub(r'd\.filename\s*=\s*:filename', '', sql)
                print(f"Modified SQL: {sql}")
            elif doc_filename and ':filename' in sql:
                params['filename'] = doc_filename

            with self.db.get_readonly_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)

                columns = [col[0].lower() for col in cursor.description]
                results = []

                for row in cursor:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]

                        if hasattr(value, 'read'):
                            value = value.read()
                        elif isinstance(value, dict):
                            pass
                        elif col == 'metadata' and isinstance(value, str):
                            try:
                                value = json.loads(value)
                            except:
                                value = {}

                        row_dict[col] = value

                    chunk = self._sql_row_to_chunk(row_dict)
                    results.append(chunk)

                print(f"SQL returned {len(results)} results")

                return {
                    'chunks': results,
                    'confidence': confidence,
                    'query_type': query_type
                }

        except Exception as e:
            print(f"SQL search error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'chunks': [],
                'confidence': 0.0,
                'query_type': 'hybrid'
            }

    def _sql_row_to_chunk(self, row: Dict) -> Dict:
        metadata = row.get('attributes') or row.get('metadata')
        if metadata is None:
            metadata = {}
        elif isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        chunk_text = row.get('content', '')
        if not chunk_text:
            title = row.get('name', '')
            filename = row.get('file_name', '')
            total_pages = row.get('page_count', 0)

            if title or filename:
                parts = []
                if title:
                    parts.append(f"เอกสาร: {title}")
                if filename:
                    parts.append(f"ไฟล์: {filename}")
                if total_pages:
                    parts.append(f"จำนวน {total_pages} หน้า")
                chunk_text = ' - '.join(parts)
            else:
                chunk_text = "ไม่มีข้อมูล"

        return {
            'chunk_id': row.get('id', 0),
            'doc_id': row.get('document_id', 0),
            'text': chunk_text,
            'page': row.get('page_ref', 0),
            'type': row.get('category', 'text'),
            'filename': row.get('file_name', ''),
            'title': row.get('name', ''),
            'score': 1.0,
            'source': 'sql',
            'metadata': metadata
        }

    def _merge_and_dedupe(self, vector_chunks: List[Dict], 
                         sql_chunks: List[Dict]) -> List[Dict]:
        def chunk_key(chunk):
            return f"{chunk.get('doc_id', 0)}_{chunk.get('page', 0)}_{chunk.get('chunk_id', 0)}"
        
        seen = {}
        merged = []
        
        for chunk in sql_chunks:
            key = chunk_key(chunk)
            chunk['search_method'] = 'sql'
            seen[key] = chunk
            merged.append(chunk)
        
        for chunk in vector_chunks:
            key = chunk_key(chunk)
            if key not in seen:
                chunk['search_method'] = 'vector'
                seen[key] = chunk
                merged.append(chunk)
            else:
                seen[key]['score'] = min(1.0, seen[key]['score'] * 1.2)
                seen[key]['search_method'] = 'both'
        
        return merged
    
    def _smart_merge(self, vector_chunks: List[Dict], sql_chunks: List[Dict], 
                    weights: Dict[str, float]) -> List[Dict]:
        all_chunks = []

        for chunk in vector_chunks:
            chunk['weighted_score'] = chunk.get('score', 0.5) * weights['vector']
            chunk['sources'] = ['vector']
            all_chunks.append(chunk)

        for chunk in sql_chunks:
            existing = self._find_similar_chunk(chunk, all_chunks)
            if existing:
                existing['weighted_score'] += 1.0 * weights['sql']
                existing['sources'].append('sql')
            else:
                chunk['weighted_score'] = 1.0 * weights['sql']
                chunk['sources'] = ['sql']
                all_chunks.append(chunk)

        all_chunks.sort(key=lambda x: x['weighted_score'], reverse=True)

        return self._apply_smart_diversity(all_chunks)
    
    def _find_similar_chunk(self, target_chunk: Dict, chunk_list: List[Dict]) -> Optional[Dict]:
        target_key = f"{target_chunk.get('doc_id', 0)}_{target_chunk.get('page', 0)}_{target_chunk.get('chunk_id', 0)}"

        for chunk in chunk_list:
            chunk_key = f"{chunk.get('doc_id', 0)}_{chunk.get('page', 0)}_{chunk.get('chunk_id', 0)}"
            if chunk_key == target_key:
                return chunk

        return None
    
    def _apply_smart_diversity(self, chunks: List[Dict]) -> List[Dict]:
        diverse_chunks = []
        page_counts = {}
        doc_counts = {}

        for chunk in chunks:
            page_key = f"{chunk.get('doc_id', 0)}_{chunk.get('page', 0)}"
            doc_id = chunk.get('doc_id', 0)

            page_count = page_counts.get(page_key, 0)
            doc_count = doc_counts.get(doc_id, 0)

            diversity_penalty = 1.0
            if page_count >= 2:
                diversity_penalty *= 0.7
            if doc_count >= 5:
                diversity_penalty *= 0.8

            chunk['final_weighted_score'] = chunk['weighted_score'] * diversity_penalty
            diverse_chunks.append(chunk)

            page_counts[page_key] = page_count + 1
            doc_counts[doc_id] = doc_count + 1

        diverse_chunks.sort(key=lambda x: x['final_weighted_score'], reverse=True)

        return diverse_chunks
    
    def _analyze_query_intent(self, query: str) -> Dict:
        query_lower = query.lower()
    
        metadata_patterns = {
            'page_count': ['จำนวนหน้า', 'กี่หน้า', 'pages count', 'how many pages', 'เกิน', 'มากกว่า', 'น้อยกว่า', 'ไม่เกิน'],
            'date': ['วันที่', 'เมื่อไหร่', 'date', 'when', 'อัพโหลด'],
            'title': ['ชื่อ', 'title', 'เรื่อง', 'ชื่อเรื่อง'],
            'list': ['ทั้งหมด', 'all', 'list', 'แสดงรายการ', 'ไหนบ้าง', 'อะไรบ้าง'],
            'document_query': ['ไฟล์ไหน', 'เอกสารไหน', 'วิทยานิพนธ์ไหน', 'which document', 'which file']
        }
    
        content_patterns = {
            'summary': ['สรุป', 'summary', 'ย่อ', 'บทคัดย่อ'],
            'detail': ['รายละเอียด', 'detail', 'อธิบาย', 'explain'],
            'specific': ['บทที่', 'chapter', 'หัวข้อ', 'section', 'ตอนที่'],
            'research': ['ผลการวิจัย', 'วิธีการ', 'results', 'methodology'],
            'page_content': ['เนื้อหาหน้า', 'ขอเนื้อหา', 'content of page', 'ข้อมูลหน้า', 'หน้า \\d+']
        }
    
        overview_patterns = ['สรุป', 'ภาพรวม', 'overview', 'summary', 'เกี่ยวกับอะไร', 'คืออะไร', 'พูดถึงอะไร', 'เนื้อหาหลัก']
    
        intent = {
            'primary_focus': 'unknown',
            'requires_content': False,
            'requires_metadata': False,
            'confidence': 0.5,
            'is_overview_query': False,
            'needs_document_selection': False,
            'preferred_chunk_types': [],
            'is_page_range_query': False,
            'is_page_query': False,
            'is_multiple_pages_query': False,
            'page_range': None,
            'page_numbers': []
        }
    
        # Check for single page pattern
        single_page_match = re.search(r'หน้า\s*(\d+)(?!\s*[-–ถึงและ])|page\s*(\d+)(?!\s*[-–to])', query_lower)
        if single_page_match:
            page_num = int(single_page_match.group(1) or single_page_match.group(2))
            intent['is_page_query'] = True
            intent['requires_content'] = True
            intent['page_numbers'] = [page_num]
            intent['needs_document_selection'] = True
    
        # Check for multiple specific pages (e.g., "หน้า 59 และ 78", "หน้า 10, 20, 30")
        multiple_pages = re.findall(r'\d+', query_lower)
        if len(multiple_pages) >= 2 and any(word in query_lower for word in ['หน้า', 'page']) and any(word in query_lower for word in ['และ', 'กับ', ',', 'and']):
            intent['is_multiple_pages_query'] = True
            intent['requires_content'] = True
            intent['page_numbers'] = [int(p) for p in multiple_pages]
            intent['needs_document_selection'] = True
    
        # Check for page range patterns
        page_range_patterns = [
            r'หน้า\s*(\d+)\s*[-–]\s*(\d+)',
            r'page\s*(\d+)\s*[-–]\s*(\d+)',
            r'ตั้งแต่หน้า\s*(\d+)\s*ถึง\s*(\d+)',
            r'จากหน้า\s*(\d+)\s*ถึง\s*(\d+)',
            r'หน้า\s*(\d+)\s*ถึง\s*(\d+)',
            r'from page\s*(\d+)\s*to\s*(\d+)',
            r'ตั้งแต่หน้า\s*(\d+)\s*ถึงหน้า\s*(\d+)',
            r'จากหน้า\s*(\d+)\s*ไปถึงหน้า\s*(\d+)',
        ]
    
        page_range_match = None
        for pattern in page_range_patterns:
            match = re.search(pattern, query_lower)
            if match:
                page_range_match = match
                break
            
        if page_range_match:
            intent['is_page_range_query'] = True
            intent['requires_content'] = True
            start_page = int(page_range_match.group(1))
            end_page = int(page_range_match.group(2))
            intent['page_range'] = (start_page, end_page)
            intent['needs_document_selection'] = True
    
        metadata_score = 0
        content_score = 0
        overview_score = 0
    
        # ตรวจสอบ metadata patterns
        for category, patterns in metadata_patterns.items():
            if any(p in query_lower for p in patterns):
                metadata_score += 1
                intent['requires_metadata'] = True
                # ถ้าเป็น document_query หรือ page_count ให้ score เพิ่ม
                if category in ['document_query', 'page_count']:
                    metadata_score += 1
    
        # ตรวจสอบ content patterns
        for category, patterns in content_patterns.items():
            if category == 'page_content':
                for pattern in patterns:
                    if re.search(pattern, query_lower):
                        content_score += 2
                        intent['requires_content'] = True
                        break
            else:
                if any(p in query_lower for p in patterns):
                    content_score += 1
                    intent['requires_content'] = True
    
        # ตรวจสอบ overview patterns
        for pattern in overview_patterns:
            if pattern in query_lower:
                overview_score += 1
                intent['is_overview_query'] = True
    
        # ตรวจสอบว่าต้องการเลือกเอกสารหรือไม่
        if ('เอกสารนี้' in query_lower or 'this document' in query_lower) and overview_score > 0:
            intent['needs_document_selection'] = True
    
        # กำหนด preferred chunk types สำหรับ overview
        if intent['is_overview_query']:
            intent['preferred_chunk_types'] = ['abstract', 'introduction', 'summary', 'conclusion']
    
        # กำหนด primary focus
        if intent['is_page_range_query'] or intent['is_page_query'] or intent['is_multiple_pages_query']:
            intent['primary_focus'] = 'content'
            intent['confidence'] = 0.9
        elif overview_score > 0 and overview_score >= max(metadata_score, content_score):
            intent['primary_focus'] = 'overview'
            intent['confidence'] = min(0.9, 0.6 + overview_score * 0.1)
        elif metadata_score > content_score:
            intent['primary_focus'] = 'metadata'
            intent['confidence'] = min(0.9, 0.5 + metadata_score * 0.2)
        elif content_score > metadata_score:
            intent['primary_focus'] = 'content'
            intent['confidence'] = min(0.9, 0.5 + content_score * 0.2)
        else:
            intent['primary_focus'] = 'hybrid'
            intent['confidence'] = 0.6
    
        return intent
    
    def _apply_overview_boosting(self, chunks: List[Dict], query_intent: Dict) -> List[Dict]:
        if not query_intent.get('is_overview_query', False):
            return chunks
        
        boosted_chunks = []
        preferred_types = query_intent.get('preferred_chunk_types', [])
        
        for chunk in chunks:
            boosted_chunk = chunk.copy()
            boost_factor = 1.0
            
            if chunk.get('type') in preferred_types:
                boost_factor *= 1.5
            
            chunk_text_lower = chunk.get('text', '').lower()
            overview_keywords = ['บทคัดย่อ', 'abstract', 'สรุป', 'summary', 'บทนำ', 'introduction', 
                               'วัตถุประสงค์', 'objective', 'ภาพรวม', 'overview']
            
            keyword_count = sum(1 for keyword in overview_keywords if keyword in chunk_text_lower)
            if keyword_count > 0:
                boost_factor *= (1.0 + 0.2 * keyword_count)
            
            if 'score' in boosted_chunk:
                boosted_chunk['score'] *= boost_factor
            if 'weighted_score' in boosted_chunk:
                boosted_chunk['weighted_score'] *= boost_factor
            if 'final_weighted_score' in boosted_chunk:
                boosted_chunk['final_weighted_score'] *= boost_factor
            
            boosted_chunk['overview_boost'] = boost_factor
            boosted_chunks.append(boosted_chunk)
        
        boosted_chunks.sort(key=lambda x: x.get('final_weighted_score', x.get('weighted_score', x.get('score', 0))), reverse=True)
        
        return boosted_chunks