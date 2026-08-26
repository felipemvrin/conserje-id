"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.schemas import ConserjeResponse, LoginRequest, TokenResponse
from app.security import authenticate_conserje, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Login endpoint for conserjes.

    Returns JWT access token on success.
    """
    conserje = authenticate_conserje(db, request.rut, request.password)

    if not conserje:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid RUT or password",
        )

    access_token = create_access_token(data={"sub": str(conserje.id)})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=ConserjeResponse)
async def get_current_user(db: Session = Depends(get_db)) -> ConserjeResponse:
    """Get current authenticated conserje info."""
    # This endpoint would need authentication middleware added to main.py
    # For now, it's a placeholder
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)
