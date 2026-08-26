"""Security and authentication utilities."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import Conserje

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: move to environment variable
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
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
        conserje_id: int = payload.get("sub")
        if conserje_id is None:
            raise JWTError("Invalid token: no sub claim")
        return {"conserje_id": conserje_id}
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
) -> Optional[Conserje]:
    """Authenticate conserje by RUT and password."""
    conserje = db.query(Conserje).filter(Conserje.rut == rut).first()
    if not conserje or not verify_password(password, conserje.password_hash):
        return None
    return conserje
