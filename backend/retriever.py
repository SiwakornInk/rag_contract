from typing import List, Dict, Optional, Tuple
from database import OracleVectorDB
from embeddings import EmbeddingGenerator
from reranker import Reranker
import json
import re

class DocumentRetriever:
    def __init__(self, db: OracleVectorDB, embedder: EmbeddingGenerator):
        self.db = db
        self.embedder = embedder
        self.reranker = Reranker()  # Initialize reranker
        self.max_context_length = 15000
        self.use_reranker = True  # Flag to enable/disable reranker
        
    def _parse_json(self, data):
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except:
                return {}
        return {}
    
    def retrieve(self, query: str, doc_filename: Optional[str] = None, 
                top_k: int = 10, allowed_levels: Optional[List[str]] = None) -> List[Dict]:

        # Check if this is a page-specific query
        page_match = re.search(r'หน้า\s*(\d+)|page\s*(\d+)', query.lower())
        if page_match:
            page_number = int(page_match.group(1) or page_match.group(2))

            # If asking about a specific page, get that page directly
            if doc_filename:
                page_content = self.get_page_content(doc_filename, page_number)
                if page_content:
                    # Convert page content to chunk format
                    formatted_chunks = []
                    for i, content in enumerate(page_content):
                        formatted_chunks.append({
                            'text': content['text'],
                            'page': page_number,
                            'type': content['type'],
                            'filename': doc_filename,
                            'title': '',  # Will be filled from DB
                            'score': 1.0,  # Perfect match
                            'rerank_score': 1.0,
                            'final_score': 1.0,
                            'metadata': content.get('metadata', {})
                        })

                    # Also get surrounding pages for context
                    surrounding_chunks = []
                    for offset in [-1, 1]:  # Previous and next page
                        nearby_page = page_number + offset
                        if nearby_page > 0:
                            nearby_content = self.get_page_content(doc_filename, nearby_page)
                            for content in nearby_content:
                                surrounding_chunks.append({
                                    'text': content['text'],
                                    'page': nearby_page,
                                    'type': content['type'],
                                    'filename': doc_filename,
                                    'title': '',
                                    'score': 0.5,  # Lower score for context
                                    'rerank_score': 0.5,
                                    'final_score': 0.5,
                                    'metadata': content.get('metadata', {})
                                })

                    # Combine and limit
                    all_chunks = formatted_chunks + surrounding_chunks
                    return all_chunks[:top_k]
                else:
                    # Page not found, return empty with a helpful message
                    return []

        # For non-page-specific queries, continue with normal flow
        # Adjust top_k based on query type
        adjusted_top_k = self._adjust_top_k(query, top_k)

        # Generate query embedding
        query_embedding = self.embedder.encode(query)

        # Get document ID if specific document requested
        doc_id = None
        if doc_filename:
            doc = self.db.get_document_by_filename(doc_filename)
            if doc:
                doc_id = doc['doc_id']

        # Retrieve more candidates for reranking
        # Rule of thumb: retrieve 3-5x more than needed
        num_candidates = min(adjusted_top_k * 4, 50) if self.use_reranker else adjusted_top_k

        # Get initial chunks from vector search
        chunks = self.db.search_similar_chunks(
            query_embedding, 
            doc_id, 
            num_candidates
        )
        if allowed_levels:
            chunks = [c for c in chunks if c.get('classification') in allowed_levels]

        # Convert to format for reranker
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunk = {
                'text': chunk['chunk_text'],
                'page': chunk['page_number'],
                'type': chunk['chunk_type'],
                'filename': chunk['filename'],
                'title': chunk['title'],
                'classification': chunk.get('classification'),
                'score': 1 - chunk['distance'],  # Convert distance to similarity
                'metadata': chunk.get('metadata', {})
            }
            formatted_chunks.append(formatted_chunk)

        # Apply reranking if enabled
        if self.use_reranker and formatted_chunks:
            try:
                formatted_chunks = self.reranker.rerank(
                    query, 
                    formatted_chunks, 
                    top_k=adjusted_top_k * 2  # Keep more for post-processing
                )
            except Exception as e:
                print(f"Reranking failed: {e}, falling back to vector search results")

        # Post-process chunks
        final_chunks = self._post_process_chunks(
            formatted_chunks, 
            query, 
            adjusted_top_k
        )

        # Add surrounding context if needed
        if self._needs_extended_context(query):
            final_chunks = self._add_surrounding_chunks(final_chunks, doc_id)
    
        return final_chunks
    
    def _adjust_top_k(self, query: str, default_top_k: int) -> int:
        """Adjust number of chunks based on query type"""
        query_lower = query.lower()
        
        # Comprehensive queries
        if any(word in query_lower for word in [
            'สรุป', 'อธิบาย', 'เปรียบเทียบ', 'วิเคราะห์', 
            'ทั้งหมด', 'รายละเอียด', 'summary', 'explain', 
            'compare', 'analyze', 'detail', 'ขั้นตอน', 'วิธีการ',
            'comprehensive', 'ภาพรวม', 'overview'
        ]):
            return min(25, default_top_k * 2)
        
        # Specific queries
        elif any(word in query_lower for word in [
            'คืออะไร', 'หมายถึง', 'definition', 'what is',
            'กี่', 'เท่าไหร่', 'how many', 'how much',
            'ใช่หรือไม่', 'จริงหรือไม่', 'yes or no'
        ]):
            return 10
        
        # Page-specific queries
        elif re.search(r'หน้า\s*\d+|page\s*\d+', query_lower):
            return 5
        
        # Table/figure queries
        elif any(word in query_lower for word in ['ตาราง', 'table', 'รูป', 'figure', 'กราฟ', 'chart']):
            return 15
        
        return 15
    
    def _needs_extended_context(self, query: str) -> bool:
        """Check if query needs extended context"""
        extended_keywords = [
            'บทที่', 'chapter', 'section', 'ทั้งบท',
            'ผลการวิจัย', 'results', 'methodology',
            'สรุปผล', 'conclusion', 'discussion',
            'ขั้นตอน', 'process', 'procedure'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in extended_keywords)
    
    def _post_process_chunks(self, chunks: List[Dict], query: str, top_k: int) -> List[Dict]:
        """Post-process chunks after reranking"""
        if not chunks:
            return []
        
        # Remove near-duplicates
        unique_chunks = self._remove_near_duplicates(chunks)
        
        # Ensure minimum quality
        quality_chunks = [
            chunk for chunk in unique_chunks 
            if len(chunk['text']) >= 100  # Minimum text length
        ]
        
        # If we filtered out too many, add some back
        if len(quality_chunks) < top_k // 2:
            quality_chunks = unique_chunks[:top_k]
        
        # Limit to requested number
        return quality_chunks[:top_k]
    
    def _remove_near_duplicates(self, chunks: List[Dict], similarity_threshold: float = 0.9) -> List[Dict]:
        """Remove chunks that are too similar"""
        if not chunks:
            return []
        
        unique_chunks = [chunks[0]]
        
        for chunk in chunks[1:]:
            is_duplicate = False
            
            for unique_chunk in unique_chunks:
                # Simple text similarity check
                overlap = self._calculate_text_overlap(chunk['text'], unique_chunk['text'])
                if overlap > similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def _calculate_text_overlap(self, text1: str, text2: str) -> float:
        """Calculate simple text overlap ratio"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _add_surrounding_chunks(self, chunks: List[Dict], doc_id: Optional[int]) -> List[Dict]:
        """Add surrounding chunks for better context"""
        if not chunks or not doc_id:
            return chunks
        
        # Get unique pages
        pages = set(chunk['page'] for chunk in chunks)
        
        # Determine surrounding pages to fetch
        surrounding_pages = set()
        for page in pages:
            # Add previous and next page
            surrounding_pages.add(page - 1)
            surrounding_pages.add(page + 1)
        
        # Remove pages we already have
        surrounding_pages = surrounding_pages - pages
        
        # Fetch surrounding chunks
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if surrounding_pages:
                page_list = list(surrounding_pages)
                placeholders = ','.join([str(p) for p in page_list])
                # Fetch context from new schema tables
                query = f"""
                    SELECT c.content, c.category, c.page_ref, c.sequence_num, c.attributes,
                           d.file_name, d.name
                    FROM content_segments c
                    JOIN documents d ON c.document_id = d.id
                    WHERE c.document_id = :doc_id
                      AND c.page_ref IN ({placeholders})
                    ORDER BY c.page_ref, c.sequence_num
                """
                cursor.execute(query, {'doc_id': doc_id})
                for row in cursor:
                    chunks.append({
                        'text': row[0].read() if row[0] else '',
                        'type': row[1],
                        'page': row[2],
                        'filename': row[5],
                        'title': row[6],
                        'score': 0.3,
                        'rerank_score': 0.3,
                        'final_score': 0.3,
                        'metadata': self._parse_json(row[4])
                    })
        
        # Sort by page number for coherent reading
        chunks.sort(key=lambda x: (x['page'], x.get('chunk_order', 0)))
        
        # Apply context size limit
        return self._limit_context_size(chunks)
    
    def _limit_context_size(self, chunks: List[Dict]) -> List[Dict]:
        """Limit total context size"""
        total_length = 0
        limited_chunks = []
        
        # First pass: include all high-scoring chunks
        for chunk in chunks:
            if chunk.get('final_score', chunk.get('rerank_score', chunk.get('score', 0))) > 0.5:
                chunk_length = len(chunk['text'])
                if total_length + chunk_length <= self.max_context_length:
                    limited_chunks.append(chunk)
                    total_length += chunk_length
        
        # Second pass: add remaining chunks if space available
        for chunk in chunks:
            if chunk not in limited_chunks:
                chunk_length = len(chunk['text'])
                if total_length + chunk_length <= self.max_context_length:
                    limited_chunks.append(chunk)
                    total_length += chunk_length
        
        return limited_chunks
    
    def get_page_content(self, filename: str, page_number: int) -> List[Dict]:
        """Get all content from a specific page"""
        doc = self.db.get_document_by_filename(filename)
        if not doc:
            return []
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT content, category, sequence_num, attributes
                FROM content_segments
                WHERE document_id = :doc_id AND page_ref = :page
                ORDER BY sequence_num
                """,
                {'doc_id': doc['doc_id'], 'page': page_number}
            )
            results = []
            for row in cursor:
                results.append({
                    'text': row[0].read() if row[0] else '',
                    'type': row[1],
                    'order': row[2],
                    'metadata': self._parse_json(row[3])
                })
            return results