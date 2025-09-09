import os
import time
from typing import Optional
from fastapi import HTTPException, Depends, Header, Query
from pydantic import BaseModel
from jose import jwt, JWTError
import bcrypt
import oracledb
from config import Config

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")
JWT_ALG = "HS256"


LEVEL_ORDER = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
ROLES = ["USER", "STAFF", "ANALYST", "ADMIN"]

class TokenData(BaseModel):
    username: str
    role: str
    max_level: str
    uid: int

def verify_password(password: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hash_.encode('utf-8'))
    except Exception:
        raise HTTPException(status_code=500, detail="Password verify error")

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_token(data: dict, expires_seconds: int = 8*3600) -> str:
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_seconds
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_db_conn():
    dsn = Config.build_dsn()
    return oracledb.connect(user=Config.DB_USER, password=Config.DB_PASSWORD, dsn=dsn)

def authenticate_user(username: str, password: str):
    with get_db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, role, max_level FROM users WHERE username = :u", u=username)
        row = cur.fetchone()
        if not row:
            return None
        if not verify_password(password, row[2]):
            return None
        return {"id": row[0], "username": row[1], "role": row[3], "max_level": row[4]}

def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    return TokenData(
        username=payload.get("sub"),
        role=payload.get("role"),
        max_level=payload.get("max_level"),
        uid=payload.get("uid")
    )

def get_current_user_flexible(authorization: Optional[str] = Header(None), token: Optional[str] = Query(None)) -> TokenData:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ", 1)[1]
    elif token:
        raw_token = token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(raw_token)
    return TokenData(
        username=payload.get("sub"),
        role=payload.get("role"),
        max_level=payload.get("max_level"),
        uid=payload.get("uid")
    )

def ensure_level(doc_level: str, user: TokenData):
    order = {lvl: i for i, lvl in enumerate(LEVEL_ORDER, start=1)}
    if order.get(doc_level, 999) > order.get(user.max_level, 0):
        raise HTTPException(status_code=403, detail="Access denied for this classification")

def ensure_can_upload(user: TokenData):
    if user.max_level != "SECRET":
        raise HTTPException(status_code=403, detail="Only top-level users can upload")

def has_access(user: TokenData, doc_level: str) -> bool:
    order = {lvl: i for i, lvl in enumerate(LEVEL_ORDER, start=1)}
    return order.get(doc_level, 999) <= order.get(user.max_level, 0)

def ensure_admin(user: TokenData):
    if user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Admin only")
