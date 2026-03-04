# app/auth.py
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

pwd    = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()
ALGO   = "HS256"


def hash_password(plain: str) -> str:
    return pwd.hash(plain)


def check_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)


def create_token(data: dict, expires_minutes: int = 1440) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGO)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


def get_current_user(creds: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    return decode_token(creds.credentials)
