from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import logging
from datetime import datetime, UTC
from app.core.config import settings
from app.core.security import verify_token
from app.prisma import prisma

# Configure logging
logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Get user from database
        user = await prisma.user.find_unique(where={"id": user_id})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please refresh your token or login again.",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Expired": "true"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token. Please login again.",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Invalid": "true"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user with session validation"""
    # Check if user is banned
    if current_user.banned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is banned"
        )
    
    # Check if user has an active session
    active_session = await prisma.session.find_first(
        where={
            "user_id": current_user.id,
            "is_active": True,
            "expires_at": {"gt": datetime.now(UTC)}
        }
    )
    
    if not active_session:
        logger.warning(f"No active session found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session has expired or user has logged out. Please login again.",
            headers={"WWW-Authenticate": "Bearer", "X-Session-Expired": "true"}
        )
    
    return current_user

async def get_current_user_with_role(required_role: str, current_user = Depends(get_current_user)):
    """Get current user with specific role"""
    if current_user.role != required_role and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

async def get_admin_user(current_user = Depends(get_current_user)):
    """Get current user with admin role"""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_system_admin_super_admin_user(current_user = Depends(get_current_user)):
    """Get current user with system admin role"""
    if current_user.role != "SUPER_ADMIN" and current_user.role != "SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin or super admin access required"
        )
    return current_user
    
async def get_super_admin_user(current_user = Depends(get_current_user)):
    """Get current user with super admin role"""
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_vendor_user(current_user = Depends(get_current_user)):
    """Get current user with staff or admin role"""
    if current_user.role not in ["STAFF", "ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required"
        )
    return current_user

async def get_database():
    """Get database connection"""
    return prisma
