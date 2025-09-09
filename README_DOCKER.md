# RAG Contract - Docker (Oracle Free + Backend + Frontend)

## Stack
- Oracle Database Free (vector support)
- FastAPI backend (Python 3.11)
- Next.js 15 frontend

## Quick Start
1. (Optional) Login to Oracle Container Registry:
   - Open https://container-registry.oracle.com, accept terms for `database/free`.
   - Then login locally:

```powershell
$env:ORACLE_USERNAME="<your_oracle_account>"
$env:ORACLE_PASSWORD="<your_password>"
docker login container-registry.oracle.com -u $env:ORACLE_USERNAME -p $env:ORACLE_PASSWORD
```

2. Bring up stack:
```powershell
docker compose up -d --build
```
First startup of oracle-db can take several minutes.

3. Check logs:
```powershell
docker compose logs -f oracle-db
```
Wait until `DATABASE IS READY TO USE!` appears, backend will then connect and auto-create schema.

4. Access services:
- API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Environment Variables
Backend (in compose):
- DB_USER=appuser
- DB_PASSWORD=appuserpwd
- DB_HOST=oracle-db
- DB_PORT=1521
- DB_SERVICE=FREEPDB1
- DEEPSEEK_API_KEY= (set if using LLM features)

To set LLM key at runtime on Windows PowerShell:
```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
docker compose up -d --build
```
Or create a `.env` file at repository root with:
```
DEEPSEEK_API_KEY=sk-...
```
Compose automatically loads it.

## Data Persistence
Oracle data stored in named volume `oracle-data`.
To reset database:
```powershell
docker compose down -v
```

## Uploading Documents
Use POST /upload (multipart). The backend stores:
- documents (metadata + original PDF BLOB)
- content_segments (chunked text + vector)

Vector index is created automatically on first run (if not existing).

## Common Issues
1. Cannot pull Oracle image: ensure you accepted license in OCR portal.
2. Backend cannot connect: oracle-db not ready yet; wait or check logs.
3. Memory: Oracle Free needs ~2.5GB RAM; ensure host has available memory.

## Removing Deprecated Code
Removed features:
- Wallet / TNS based connection (replaced by thin host:port/service)
- Read-only user logic & env vars
- Legacy thesis_* table references (now unified to documents/content_segments)

## Rebuild After Changes
```powershell
docker compose build backend frontend
docker compose up -d
```

## Stopping
```powershell
docker compose down
```
