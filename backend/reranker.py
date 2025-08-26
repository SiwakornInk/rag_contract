from sentence_transformers import CrossEncoder
import torch
from typing import List, Dict, Tuple
import numpy as np
import os

class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        if self.device == 'cuda':
            print(f"✓ GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
            
            torch.cuda.empty_cache()
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
        else:
            print("⚠ No GPU detected, using CPU")
        
        print(f"Loading reranker model: {model_name}")
        
        try:
            self.model = CrossEncoder(
                model_name, 
                max_length=512, 
                device=self.device,
                trust_remote_code=True
            )
            
            if self.device == 'cuda':
                torch.cuda.empty_cache()
                
        except Exception as e:
            print(f"Failed to load primary reranker: {e}")
            print("Using fallback model")
            self.model = CrossEncoder(
                'cross-encoder/ms-marco-MiniLM-L-6-v2', 
                device=self.device
            )
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = None,
         query_intent: Dict = None) -> List[Dict]:
        """Rerank with query intent awareness"""
        
        if not chunks:
            return []
        
        pairs = []
        for chunk in chunks:
            chunk_context = self._prepare_chunk_context(chunk)
            pairs.append([query, chunk_context])
        
        try:
            batch_size = 64 if self.device == 'cuda' else 32
            all_scores = []
            
            with torch.no_grad():
                if self.device == 'cuda':
                    torch.cuda.synchronize()
                
                for i in range(0, len(pairs), batch_size):
                    batch_pairs = pairs[i:i + batch_size]
                    
                    batch_scores = self.model.predict(
                        batch_pairs, 
                        convert_to_numpy=True,
                        show_progress_bar=False
                    )
                    all_scores.extend(batch_scores)
                
                if self.device == 'cuda':
                    torch.cuda.synchronize()
            
            scores = np.array(all_scores)
            
        except Exception as e:
            print(f"Reranking error: {e}")
            return chunks
        
        reranked_chunks = []
        for chunk, score in zip(chunks, scores):
            reranked_chunk = chunk.copy()
            reranked_chunk['rerank_score'] = float(score)
            
            if 'score' in chunk:
                reranked_chunk['final_score'] = 0.7 * float(score) + 0.3 * chunk['score']
            else:
                reranked_chunk['final_score'] = float(score)
            
            reranked_chunks.append(reranked_chunk)
        
        # Apply intent-based boosting
        if query_intent:
            for chunk in reranked_chunks:
                # Boost SQL results for metadata queries
                if query_intent['primary_focus'] == 'metadata' and 'sql' in chunk.get('sources', []):
                    chunk['final_score'] *= 1.2
                # Boost vector results for content queries
                elif query_intent['primary_focus'] == 'content' and 'vector' in chunk.get('sources', []):
                    chunk['final_score'] *= 1.1
                # Boost chunks from both sources for hybrid queries
                elif query_intent['primary_focus'] == 'hybrid' and len(chunk.get('sources', [])) > 1:
                    chunk['final_score'] *= 1.15
        
        # Sort by final score
        reranked_chunks.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Apply diversity
        reranked_chunks = self._apply_diversity(reranked_chunks, query)
        
        if self.device == 'cuda' and len(chunks) > 100:
            torch.cuda.empty_cache()
        
        return reranked_chunks[:top_k] if top_k else reranked_chunks
    
    def _prepare_chunk_context(self, chunk: Dict) -> str:
        parts = []
        
        metadata = chunk.get('metadata', {})
        if metadata.get('section'):
            parts.append(f"[หมวด: {metadata['section']}]")
        
        if chunk.get('page'):
            parts.append(f"[หน้า {chunk['page']}]")
        
        if chunk.get('type') and chunk['type'] != 'text':
            type_map = {
                'table': 'ตาราง',
                'image': 'รูปภาพ',
                'equation': 'สมการ'
            }
            parts.append(f"[{type_map.get(chunk['type'], chunk['type'])}]")
        
        parts.append(chunk['text'])
        
        return ' '.join(parts)
    
    def _apply_diversity(self, chunks: List[Dict], query: str) -> List[Dict]:
        if not self._needs_diversity(query):
            return chunks
        
        diverse_chunks = []
        seen_pages = {}
        seen_sections = {}
        
        for chunk in chunks:
            page = chunk.get('page', 0)
            section = chunk.get('metadata', {}).get('section', 'unknown')
            
            if seen_pages.get(page, 0) >= 2:
                chunk['final_score'] *= 0.85
            
            if seen_sections.get(section, 0) >= 3:
                chunk['final_score'] *= 0.8
            
            diverse_chunks.append(chunk)
            seen_pages[page] = seen_pages.get(page, 0) + 1
            seen_sections[section] = seen_sections.get(section, 0) + 1
        
        diverse_chunks.sort(key=lambda x: x['final_score'], reverse=True)
        
        return diverse_chunks
    
    def _needs_diversity(self, query: str) -> bool:
        diversity_keywords = [
            'ทั้งหมด', 'สรุป', 'เปรียบเทียบ', 'วิเคราะห์', 'ภาพรวม',
            'all', 'summary', 'compare', 'analyze', 'overview'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in diversity_keywords)
    
    def get_device_info(self) -> Dict:
        info = {
            'device': self.device,
            'device_name': 'CPU',
            'memory_gb': None
        }
        
        if self.device == 'cuda':
            info['device_name'] = torch.cuda.get_device_name(0)
            info['memory_gb'] = torch.cuda.get_device_properties(0).total_memory / 1024**3
            info['memory_used_gb'] = torch.cuda.memory_allocated(0) / 1024**3
            info['memory_cached_gb'] = torch.cuda.memory_reserved(0) / 1024**3
        
        return info