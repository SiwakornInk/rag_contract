import oracledb
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class OracleVectorDB:
    def __init__(self):
        self.pool = None
        self.init_pool()
    
    def init_pool(self):
        self.pool = oracledb.create_pool(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            dsn=os.getenv('DB_DSN'),
            config_dir=os.getenv('DB_WALLET_PATH'),
            wallet_location=os.getenv('DB_WALLET_PATH'),
            wallet_password=os.getenv('DB_WALLET_PASSWORD'),
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
    
    def insert_document(self, filename: str, title: str, abstract: str, total_pages: int, metadata: Dict, pdf_file: Optional[bytes] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO documents (file_name, name, page_count, created_at, description, properties, file_data)
                VALUES (:1, :2, :3, CURRENT_TIMESTAMP, :4, :5, :6)
            """, [filename, title, total_pages, abstract, json.dumps(metadata), pdf_file])
            
            cursor.execute("SELECT doc_seq.CURRVAL FROM DUAL")
            doc_id = cursor.fetchone()[0]
            
            conn.commit()
            return doc_id
    
    def insert_chunk(self, doc_id: int, chunk_text: str, chunk_type: str, 
                    page_number: int, chunk_order: int, embedding: List[float], metadata: Dict):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            embedding_array = np.array(embedding, dtype=np.float32)
            embedding_str = str(embedding_array.tolist())
            
            cursor.execute("""
                INSERT INTO content_segments 
                (document_id, category, page_ref, sequence_num, vector_data, attributes, content)
                VALUES (:1, :2, :3, :4, TO_VECTOR(:5), :6, :7)
            """, [doc_id, chunk_type, page_number, chunk_order, 
                  embedding_str, json.dumps(metadata), chunk_text])
            conn.commit()
    
    def search_similar_chunks(self, query_embedding: List[float], doc_id: Optional[int] = None, 
                            top_k: int = 10) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            embedding_str = str(query_embedding)
            
            base_query = """
                SELECT c.id, c.document_id, c.category, 
                       c.page_ref, c.sequence_num, c.attributes,
                       d.file_name, d.name,
                       VECTOR_DISTANCE(c.vector_data, TO_VECTOR(:1), COSINE) as distance,
                       c.content
                FROM content_segments c
                JOIN documents d ON c.document_id = d.id
                WHERE 1=1
            """
            
            params = [embedding_str]
            
            if doc_id:
                base_query += " AND c.document_id = :2"
                params.append(doc_id)
            
            base_query += " ORDER BY distance FETCH FIRST :3 ROWS ONLY"
            params.append(top_k)
            
            cursor.execute(base_query, params)
            
            results = []
            for row in cursor:
                results.append({
                    'chunk_id': row[0],
                    'doc_id': row[1],
                    'chunk_type': row[2],
                    'page_number': row[3],
                    'chunk_order': row[4],
                    'metadata': self._parse_json(row[5]),
                    'filename': row[6],
                    'title': row[7],
                    'distance': row[8],
                    'chunk_text': row[9].read() if row[9] else ''
                })
            
            return results
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, file_name, name, page_count, properties, description
                FROM documents
                WHERE file_name = :1
            """, [filename])
            
            row = cursor.fetchone()
            if row:
                return {
                    'doc_id': row[0],
                    'filename': row[1],
                    'title': row[2],
                    'total_pages': row[3],
                    'metadata': self._parse_json(row[4]),
                    'abstract': row[5].read() if row[5] else ''
                }
            return None
    
    def list_documents(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, file_name, name, page_count, created_at
                FROM documents
                ORDER BY created_at DESC
            """)
            
            results = []
            for row in cursor:
                results.append({
                    'doc_id': row[0],
                    'filename': row[1],
                    'title': row[2],
                    'total_pages': row[3],
                    'upload_date': row[4].isoformat() if row[4] else None
                })
            
            return results
    
    def create_vector_index(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    CREATE VECTOR INDEX idx_segment_vector 
                    ON content_segments(vector_data) 
                    ORGANIZATION INMEMORY NEIGHBOR GRAPH
                    DISTANCE COSINE
                    WITH TARGET ACCURACY 95
                """)
                conn.commit()
                print("Vector index created successfully")
            except Exception as e:
                print(f"Index might already exist: {e}")

    def execute_read_only_sql(self, sql: str, params: Dict = None) -> List[Dict]:
        """Execute read-only SQL with parameters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SET TRANSACTION READ ONLY")

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            columns = [col[0].lower() for col in cursor.description]

            results = []
            for row in cursor.fetchall():
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    if hasattr(value, 'read'):
                        value = value.read()
                    row_dict[col] = value
                results.append(row_dict)

            return results
        
    def get_readonly_connection(self):
        """Get read-only connection"""
        from config import Config
        
        if Config.USE_READONLY_USER:
            conn = oracledb.connect(
                user=Config.SQL_READ_ONLY_USER,
                password=Config.SQL_READ_ONLY_PASSWORD,
                dsn=os.getenv('DB_DSN'),
                config_dir=os.getenv('DB_WALLET_PATH'),
                wallet_location=os.getenv('DB_WALLET_PATH'),
                wallet_password=os.getenv('DB_WALLET_PASSWORD')
            )
        else:
            conn = self.get_connection()
        
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION READ ONLY")
        
        return conn
    
    def get_pdf_file(self, doc_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        """Get PDF file content by document ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_data, file_name
                FROM documents
                WHERE id = :1
            """, [doc_id])
            
            row = cursor.fetchone()
            if row:
                pdf_blob = row[0]
                filename = row[1]
                
                try:
                    print(f"Fetching PDF for doc_id {doc_id}, filename: {filename}")
                except UnicodeEncodeError:
                    print(f"Fetching PDF for doc_id {doc_id}, filename: [Thai filename]")
                
                print(f"PDF BLOB is None: {pdf_blob is None}")
                
                if pdf_blob:
                    if hasattr(pdf_blob, 'read'):
                        pdf_data = pdf_blob.read()
                    else:
                        pdf_data = pdf_blob
                    
                    print(f"PDF data size: {len(pdf_data) if pdf_data else 0} bytes")
                    return pdf_data, filename
                else:
                    print(f"No PDF data found for doc_id {doc_id}")
            else:
                print(f"No document found with doc_id {doc_id}")
                
            return None, None
    
    def get_pdf_file_by_filename(self, filename: str) -> Optional[bytes]:
        """Get PDF file content by filename"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_data
                FROM documents
                WHERE file_name = :1
            """, [filename])
            
            row = cursor.fetchone()
            if row and row[0]:
                return row[0].read() if hasattr(row[0], 'read') else row[0]
            return None