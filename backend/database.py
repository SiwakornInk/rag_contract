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
                        metadata: Dict, pdf_file: Optional[bytes] = None, classification: str = "PUBLIC") -> int:
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
                INSERT INTO documents (file_name, name, page_count, created_at, classification_level, properties, file_data)
                VALUES (:file_name, :name, :page_count, CURRENT_TIMESTAMP, :classification_level, :properties, :file_data)
                RETURNING id INTO :id
                """,
                file_name=filename,
                name=title,
                page_count=total_pages,
                classification_level=classification,
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
                "d.file_name, d.name, d.classification_level, VECTOR_DISTANCE(c.vector_data, TO_VECTOR(:embed), COSINE) distance, c.content "
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
                    'classification': r[8],
                    'distance': r[9],
                    'chunk_text': r[10].read() if r[10] else ''
                })
            return results
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, file_name, name, page_count, properties, classification_level FROM documents WHERE file_name = :fn",
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
                'abstract': metadata.get('abstract', ''),
                'classification': row[5]
            }

    def get_document_meta(self, doc_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, file_name, classification_level FROM documents WHERE id = :i", i=doc_id)
            row = cur.fetchone()
            if not row:
                return None
            return { 'doc_id': row[0], 'filename': row[1], 'classification': row[2] }
    
    def list_documents(self, max_level: Optional[str] = None) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            level_order = {"PUBLIC":1, "INTERNAL":2, "CONFIDENTIAL":3, "SECRET":4}
            if max_level and max_level in level_order:
                allowed = level_order[max_level]
                cur.execute(
                    "SELECT id, file_name, name, page_count, created_at, classification_level FROM documents ORDER BY created_at DESC"
                )
                rows = [r for r in cur.fetchall() if level_order.get(r[5], 99) <= allowed]
            else:
                cur.execute("SELECT id, file_name, name, page_count, created_at, classification_level FROM documents ORDER BY created_at DESC")
                rows = cur.fetchall()
            return [
                {
                    'doc_id': r[0],
                    'filename': r[1],
                    'title': r[2],
                    'total_pages': r[3],
                    'upload_date': r[4].isoformat() if r[4] else None,
                    'classification': r[5]
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
                cur.execute("SELECT 1 FROM user_tables WHERE table_name = 'TEMPLATES'")
                has_templates = cur.fetchone() is not None
            except Exception as e:
                raise RuntimeError(f"Schema check failed: {e}")
            if not (has_docs and has_segments):
                raise RuntimeError(
                    "Schema missing. Run database/setup.sql first (as APPUSER) before starting backend."
                )

    # ================= Templates API =================
    def insert_template(self, name: str, original_filename: str, doc_type: str, language: str,
                        file_bytes: bytes, content_text: str, created_by: str) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            id_var = cur.var(oracledb.NUMBER)
            cur.execute(
                """
                INSERT INTO templates (name, original_filename, doc_type, language, fields_json, content_text, file_data, created_by)
                VALUES (:name, :original_filename, :doc_type, :language, EMPTY_CLOB(), :content_text, :file_data, :created_by)
                RETURNING id INTO :id
                """,
                name=name,
                original_filename=original_filename,
                doc_type=doc_type,
                language=language,
                content_text=content_text,
                file_data=file_bytes,
                created_by=created_by,
                id=id_var
            )
            raw_val = id_var.getvalue()
            if isinstance(raw_val, list):
                raw_val = raw_val[0] if raw_val else None
            if raw_val is None:
                # fallback
                cur.execute("SELECT MAX(id) FROM templates")
                row = cur.fetchone()
                if not row or row[0] is None:
                    raise RuntimeError("Failed to retrieve new template id")
                new_id = int(row[0])
            else:
                new_id = int(raw_val)
            conn.commit()
            return new_id

    def update_template_fields(self, template_id: int, fields_json: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE templates SET fields_json = :f WHERE id = :i", f=fields_json, i=template_id)
            conn.commit()

    def list_templates(self) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, original_filename, doc_type, language, created_at, fields_json
                  FROM templates
                 ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = {
                    'id': r[0],
                    'name': r[1],
                    'original_filename': r[2],
                    'doc_type': r[3],
                    'language': r[4],
                    'created_at': r[5].isoformat() if r[5] else None,
                    'fields_json': r[6].read() if hasattr(r[6], 'read') else (r[6] or '')
                }
                try:
                    arr = json.loads(item['fields_json'] or '[]')
                    item['fields_count'] = len(arr) if isinstance(arr, list) else 0
                except Exception:
                    item['fields_count'] = 0
                results.append(item)
            return results

    def get_template_by_id(self, template_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, original_filename, doc_type, language, fields_json, content_text, file_data FROM templates WHERE id = :i",
                i=template_id
            )
            row = cur.fetchone()
            if not row:
                return None
            fields_json = row[5].read() if hasattr(row[5], 'read') else (row[5] or '')
            content_text = row[6].read() if hasattr(row[6], 'read') else (row[6] or '')
            file_blob = row[7]
            return {
                'id': row[0],
                'name': row[1],
                'original_filename': row[2],
                'doc_type': row[3],
                'language': row[4],
                'fields_json': fields_json,
                'content_text': content_text,
                'file_data': file_blob.read() if hasattr(file_blob, 'read') else file_blob
            }
