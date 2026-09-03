from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.core import auth
from app.schemas.user import Token
from app.db.session import get_db

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """
    Authenticate user and return JWT token.
    Uses PostgreSQL DB to read user credentials.
    """
    user = await db.fetchrow("SELECT id, username, hashed_password, role FROM public.users WHERE username = $1 AND is_active = TRUE", form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id, username, hashed_pass, role = user
    
    # In our seed, hashed_password is created by pgcrypto which uses standard bcrypt.
    # We can verify it using passlib.
    if not auth.verify_password(form_data.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": username, "role": role, "id": user_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
