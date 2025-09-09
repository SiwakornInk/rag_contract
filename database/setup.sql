-- Minimal Oracle schema reset & create (run as APPUSER)
SET SERVEROUTPUT ON

BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_segment_vector'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_segment_page'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_segment_doc'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_file_name'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE content_segments CASCADE CONSTRAINTS PURGE'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE documents CASCADE CONSTRAINTS PURGE'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP TABLE users CASCADE CONSTRAINTS PURGE'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE segment_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE doc_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE user_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

CREATE SEQUENCE doc_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE segment_seq START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE documents (
    id NUMBER DEFAULT doc_seq.NEXTVAL PRIMARY KEY,
    file_name VARCHAR2(500) NOT NULL,
    name VARCHAR2(1000),
    page_count NUMBER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    classification_level VARCHAR2(20) DEFAULT 'PUBLIC' NOT NULL,
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

CREATE UNIQUE INDEX idx_file_name ON documents(file_name);
CREATE INDEX idx_docs_classification ON documents(classification_level);
CREATE INDEX idx_segment_doc ON content_segments(document_id);
CREATE INDEX idx_segment_doc_page ON content_segments(document_id, page_ref);

-- Optional later:
-- CREATE VECTOR INDEX idx_segment_vector ON content_segments(vector_data)
--   ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95;

-- Users & Roles -----------------------------------------------------------
-- Levels (ascending security): PUBLIC < INTERNAL < CONFIDENTIAL < SECRET

CREATE SEQUENCE user_seq START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE users (
    id NUMBER DEFAULT user_seq.NEXTVAL PRIMARY KEY,
    username VARCHAR2(100) NOT NULL UNIQUE,
    password_hash VARCHAR2(200) NOT NULL,
    role VARCHAR2(50) NOT NULL,
    max_level VARCHAR2(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed admin (password: Admin123! ) bcrypt hash pre-generated
INSERT INTO users (username, password_hash, role, max_level)
VALUES ('admin', '$2b$12$6GH8Qqq6GFOLl8L/vxUv8OK93Es9UfhsYdLuzASSidKQkUyORpcRm', 'ADMIN', 'SECRET');

COMMIT;

PROMPT Schema ready with classification & auth.