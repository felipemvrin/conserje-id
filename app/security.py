"""Security and authentication utilities."""
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import Conserje

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
if SECRET_KEY == "change-me-in-production":
    logger.warning(
        "JWT_SECRET_KEY is not set; using insecure default secret. "
        "Set JWT_SECRET_KEY in production."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for FastAPI
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise JWTError("Invalid token: no sub claim")
        conserje_id = int(sub)
        return {"conserje_id": conserje_id}
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


async def get_current_conserje(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Conserje:
    """Dependency: get current authenticated conserje from token."""
    token = credentials.credentials
    token_data = verify_token(token)

    conserje = db.query(Conserje).filter(Conserje.id == token_data["conserje_id"]).first()
    if not conserje or not conserje.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conserje not found or inactive",
        )
    return conserje


def authenticate_conserje(
    db: Session, rut: str, password: str
) -> Conserje | None:
    """Authenticate conserje by RUT and password."""
    conserje = db.query(Conserje).filter(Conserje.rut == rut).first()
    if not conserje or not verify_password(password, conserje.password_hash):
        return None
    return conserje
