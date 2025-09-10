-- Safe migration to add templates table without dropping data
BEGIN
    EXECUTE IMMEDIATE 'CREATE SEQUENCE templates_seq START WITH 1 INCREMENT BY 1 NOCACHE';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF; -- sequence exists
END;
/

BEGIN
    EXECUTE IMMEDIATE '
        CREATE TABLE templates (
            id NUMBER DEFAULT templates_seq.NEXTVAL PRIMARY KEY,
            name VARCHAR2(500),
            original_filename VARCHAR2(500),
            doc_type VARCHAR2(100),
            language VARCHAR2(50),
            fields_json CLOB,
            content_text CLOB,
            file_data BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR2(100)
        )';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF; -- table exists
END;
/
