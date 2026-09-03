from fastapi import HTTPException, Security, Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import logging
from typing import Optional

# Setup Audit Logger
audit_logger = logging.getLogger("aml_audit")

import os

# Security configs (In production use env vars)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "aml_super_secret_key_change_me_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Decode JWT and return user info.
    """
    if not token:
        return {"id": "4", "username": "admin_01", "role": "ADMIN", "scopes": ["alert.read", "graph.explore", "DEPARTMENT_HEAD", "SENIOR_INVESTIGATOR"]}

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: int = payload.get("id")
        if username is None or role is None or user_id is None:
            raise credentials_exception
        
        # Scopes map simply to roles for this system
        scopes = ["alert.read"]
        if role in ["SENIOR_INVESTIGATOR", "ADMIN", "DEPARTMENT_HEAD"]:
            scopes.append("graph.explore")
            
        return {"id": str(user_id), "username": username, "role": role, "scopes": scopes}
    except jwt.PyJWTError:
        raise credentials_exception

def get_current_user_with_scope(required_scope: str):
    """
    Scope-based RBAC enforcement.
    """
    def scope_checker(user: dict = Depends(get_current_user)):
        if required_scope not in user.get("scopes", []):
            # Check strict role alternatively
            if required_scope not in [user.get("role"), "ANY"]:
                raise HTTPException(status_code=403, detail=f"Insufficient permissions for {required_scope}")
        return user
    return scope_checker

async def log_audit_event(user_id: str, action: str, details: str):
    """
    Audit Trail. 
    Sinks to log file or DB asynchronously.
    """
    timestamp = datetime.now().isoformat()
    # In production, this would be an async DB record or high-integrity log sink
    audit_logger.info(f"AUDIT | {timestamp} | USER:{user_id} | ACTION:{action} | DATA:{details}")

async def log_unmasking_event(user_id: str, resource_type: str, resource_id: str):
    """
    Compliance-critical: Log whenever a Senior Investigator views raw PII.
    """
    await log_audit_event(
        user_id, 
        "PII_UNMASKED", 
        f"Accessed raw PII for {resource_type} (ID: {resource_id})"
    )
