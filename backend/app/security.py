from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

hasher = PasswordHasher()
_sessions: dict[str, tuple[str, datetime]] = {}


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except Exception:
        return False


def create_session(user_id: str) -> str:
    token = token_urlsafe(32)
    _sessions[token] = (user_id, datetime.now(timezone.utc) + timedelta(hours=12))
    return token


def clear_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("store_session")
    record = _sessions.get(token or "")
    if not record or record[1] <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.scalar(select(User).where(User.id == UUID(record[0]), User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user

