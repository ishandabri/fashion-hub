from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import SessionRecord, User

hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except Exception:
        return False

def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()

def create_session(db: Session, user_id: str) -> tuple[str, str]:
    token, csrf = token_urlsafe(32), token_urlsafe(24)
    db.add(SessionRecord(token_hash=digest(token), csrf_token_hash=digest(csrf), user_id=UUID(user_id), expires_at=(datetime.now(timezone.utc) + timedelta(hours=12)).replace(tzinfo=None)))
    db.commit()
    return token, csrf

def clear_session(db: Session, token: str | None) -> None:
    if token:
        record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == digest(token)))
        if record:
            record.revoked_at = datetime.utcnow()
            db.commit()

def current_session(request: Request, db: Session = Depends(get_db)) -> SessionRecord:
    record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == digest(request.cookies.get("store_session") or ""), SessionRecord.revoked_at.is_(None)))
    if not record or record.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return record

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    session = current_session(request, db)
    user = db.scalar(select(User).where(User.id == session.user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user

def require_csrf(request: Request, session: SessionRecord = Depends(current_session)) -> None:
    if digest(request.headers.get("X-CSRF-Token", "")) != session.csrf_token_hash:
        raise HTTPException(status_code=403, detail="CSRF validation failed")
