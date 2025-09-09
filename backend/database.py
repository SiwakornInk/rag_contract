import oracledb
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from config import Config

load_dotenv()


class OracleVectorDB:
    def __init__(self):
        self.pool = None
        self._init_pool()
        # Verify schema exists (no auto-creation). Will raise if missing.
        self._check_schema()

    def _init_pool(self):
        """Create a simple thin connection pool to Oracle Free"""
        dsn = Config.build_dsn()
        self.pool = oracledb.create_pool(
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            dsn=dsn,
            min=2,
            max=10,
            increment=1
        )

    def get_connection(self):
        return self.pool.acquire()
    
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
    
    def insert_document(self, filename: str, title: str, abstract: str, total_pages: int,
                        metadata: Dict, pdf_file: Optional[bytes] = None) -> int:
        """Insert a document and return its generated ID.

        The former 'description' column was removed from schema; we now persist any
        provided abstract inside properties JSON under key 'abstract'.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            id_var = cur.var(oracledb.NUMBER)
            # Ensure we don't mutate caller's dict
            props = dict(metadata or {})
            if abstract:
                props.setdefault('abstract', abstract)
            cur.execute(
                """
                INSERT INTO documents (file_name, name, page_count, created_at, properties, file_data)
                VALUES (:file_name, :name, :page_count, CURRENT_TIMESTAMP, :properties, :file_data)
                RETURNING id INTO :id
                """,
                file_name=filename,
                name=title,
                page_count=total_pages,
                properties=json.dumps(props),
                file_data=pdf_file,
                id=id_var
            )
            raw_val = id_var.getvalue()
            # oracledb may return the scalar or a one-element list depending on mode
            if isinstance(raw_val, list):
                raw_val = raw_val[0] if raw_val else None
            if raw_val is None:
                raise RuntimeError("Failed to retrieve returned document ID")
            doc_id = int(raw_val)
            conn.commit()
            return doc_id
    
    def insert_chunk(self, doc_id: int, chunk_text: str, chunk_type: str,
                     page_number: int, chunk_order: int, embedding: List[float], metadata: Dict):
        with self.get_connection() as conn:
            cur = conn.cursor()
            embedding_array = np.array(embedding, dtype=np.float32)
            embedding_str = str(embedding_array.tolist())
            cur.execute(
                """
                INSERT INTO content_segments 
                (document_id, category, page_ref, sequence_num, vector_data, attributes, content)
                VALUES (:1, :2, :3, :4, TO_VECTOR(:5), :6, :7)
                """,
                [doc_id, chunk_type, page_number, chunk_order, embedding_str, json.dumps(metadata), chunk_text]
            )
            conn.commit()
    
    def search_similar_chunks(self, query_embedding: List[float], doc_id: Optional[int] = None,
                               top_k: int = 10) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            embedding_str = str(query_embedding)
            sql = (
                "SELECT c.id, c.document_id, c.category, c.page_ref, c.sequence_num, c.attributes, "
                "d.file_name, d.name, VECTOR_DISTANCE(c.vector_data, TO_VECTOR(:embed), COSINE) distance, c.content "
                "FROM content_segments c JOIN documents d ON c.document_id = d.id "
                "WHERE (:doc_id IS NULL OR c.document_id = :doc_id) "
                "ORDER BY distance FETCH FIRST :limit ROWS ONLY"
            )
            cur.execute(sql, embed=embedding_str, doc_id=doc_id, limit=top_k)
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    'chunk_id': r[0],
                    'doc_id': r[1],
                    'chunk_type': r[2],
                    'page_number': r[3],
                    'chunk_order': r[4],
                    'metadata': self._parse_json(r[5]),
                    'filename': r[6],
                    'title': r[7],
                    'distance': r[8],
                    'chunk_text': r[9].read() if r[9] else ''
                })
            return results
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, file_name, name, page_count, properties FROM documents WHERE file_name = :fn",
                fn=filename
            )
            row = cur.fetchone()
            if not row:
                return None
            metadata = self._parse_json(row[4])
            return {
                'doc_id': row[0],
                'filename': row[1],
                'title': row[2],
                'total_pages': row[3],
                'metadata': metadata,
                'abstract': metadata.get('abstract', '')
            }
    
    def list_documents(self) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, file_name, name, page_count, created_at FROM documents ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [
                {
                    'doc_id': r[0],
                    'filename': r[1],
                    'title': r[2],
                    'total_pages': r[3],
                    'upload_date': r[4].isoformat() if r[4] else None
                } for r in rows
            ]
    
    def create_vector_index(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    CREATE VECTOR INDEX idx_segment_vector 
                    ON content_segments(vector_data) 
                    ORGANIZATION INMEMORY NEIGHBOR GRAPH 
                    DISTANCE COSINE WITH TARGET ACCURACY 95
                    """
                )
                conn.commit()
                print("Vector index created")
            except Exception as e:
                print(f"Vector index existing or error: {e}")

    # Removed read-only specific functions (simplified deployment)
    
    def get_pdf_file(self, doc_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        """Get PDF file content by document ID."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT file_data, file_name FROM documents WHERE id = :id", id=doc_id)
            row = cur.fetchone()
            if not row:
                print(f"No document found with doc_id {doc_id}")
                return None, None
            pdf_blob, filename = row
            if not pdf_blob:
                print(f"No PDF data for doc_id {doc_id}")
                return None, None
            pdf_data = pdf_blob.read() if hasattr(pdf_blob, 'read') else pdf_blob
            return pdf_data, filename

    def get_pdf_file_by_filename(self, filename: str) -> Optional[bytes]:
        """Get PDF BLOB by filename."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT file_data FROM documents WHERE file_name = :fn", fn=filename)
            row = cur.fetchone()
            if row and row[0]:
                return row[0].read() if hasattr(row[0], 'read') else row[0]
            return None

    def _check_schema(self):
        """Verify required tables exist; if missing, raise with instruction."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT 1 FROM user_tables WHERE table_name = 'DOCUMENTS'")
                has_docs = cur.fetchone() is not None
                cur.execute("SELECT 1 FROM user_tables WHERE table_name = 'CONTENT_SEGMENTS'")
                has_segments = cur.fetchone() is not None
            except Exception as e:
                raise RuntimeError(f"Schema check failed: {e}")
            if not (has_docs and has_segments):
                raise RuntimeError(
                    "Schema missing. Run database/setup.sql first (as APPUSER) before starting backend."
                )
