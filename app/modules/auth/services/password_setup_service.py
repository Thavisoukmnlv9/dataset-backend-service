import jwt
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional, Tuple
import logging
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import hash_password
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response

logger = logging.getLogger(__name__)

# JWT settings for setup tokens
SETUP_TOKEN_EXPIRE_DAYS = 7  # 7 days expiration
JWT_ALGORITHM = "HS256"


class PasswordSetupService:
    """Service for handling password setup operations (for vendor onboarding)"""
    
    @staticmethod
    async def store_setup_jti(jti: str, user_id: str, expires_at: datetime) -> bool:
        """Store setup token JTI in allowlist."""
        try:
            await prisma.authresettoken.create(
                data={
                    "jti": jti,
                    "user_id": user_id,
                    "purpose": "password_setup",
                    "expires_at": expires_at
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error storing setup JTI {jti}: {str(e)}")
            return False
    
    @staticmethod
    async def is_setup_jti_valid(jti: str) -> Optional[Dict[str, Any]]:
        """Check if setup JTI is valid and not used."""
        try:
            token_record = await prisma.authresettoken.find_unique(
                where={"jti": jti}
            )
            
            if not token_record:
                return None
            
            # Check if expired
            if token_record.expires_at < datetime.now(UTC):
                return None
            
            # Check if already used
            if token_record.used_at:
                return None
            
            # Check if purpose matches
            if token_record.purpose != "password_setup":
                return None
            
            return {
                "jti": token_record.jti,
                "user_id": token_record.user_id,
                "purpose": token_record.purpose,
                "expires_at": token_record.expires_at,
                "created_at": token_record.created_at
            }
            
        except Exception as e:
            logger.error(f"Error checking setup JTI {jti}: {str(e)}")
            return None
    
    @staticmethod
    async def mark_setup_jti_used(jti: str) -> bool:
        """Mark setup JTI as used."""
        try:
            await prisma.authresettoken.update(
                where={"jti": jti},
                data={"used_at": datetime.now(UTC)}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking JTI {jti} as used: {str(e)}")
            return False
    
    @staticmethod
    async def set_user_password(user_id: str, new_password: str) -> bool:
        """Set new password for user."""
        try:
            # Hash the new password
            hashed_password = hash_password(new_password)
            
            # Update user password in User table
            await prisma.user.update(
                where={"id": user_id},
                data={"password": hashed_password}
            )
            
            logger.info(f"Password set for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting password for user {user_id}: {str(e)}")
            return False
    
    @staticmethod
    async def revoke_all_sessions(user_id: str) -> bool:
        """Revoke all user sessions and refresh tokens."""
        try:
            # Revoke all refresh tokens
            await prisma.refreshtoken.delete_many(
                where={"user_id": user_id}
            )
            
            # Revoke all sessions
            await prisma.session.delete_many(
                where={"user_id": user_id}
            )
            
            logger.info(f"All sessions revoked for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking sessions for user {user_id}: {str(e)}")
            return False
    
    @staticmethod
    async def generate_setup_token(user_id: str) -> Tuple[str, str, datetime]:
        """Generate JWT token for password setup. Returns (token, jti, expires_at)."""
        jti = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(days=SETUP_TOKEN_EXPIRE_DAYS)
        
        # Create JWT token
        token_data = {
            "sub": user_id,
            "purpose": "password_setup",
            "jti": jti,
            "iat": datetime.now(UTC).timestamp(),
            "exp": expires_at.timestamp()
        }
        
        token = jwt.encode(token_data, settings.jwt_secret, algorithm=JWT_ALGORITHM)
        
        # Store JTI in allowlist
        jti_stored = await PasswordSetupService.store_setup_jti(jti, user_id, expires_at)
        if not jti_stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate setup token. Please try again."
            )
        
        return token, jti, expires_at
    
    @staticmethod
    async def verify_setup_token(token: str) -> Dict[str, Any]:
        """Verify setup token and return user info if valid."""
        try:
            if not token:
                logger.error("Token is empty or None")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token is required"
                )
            
            logger.info("Verifying setup token (length: %d)", len(token))
            
            # Verify JWT token
            try:
                payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
                logger.info(f"Token decoded successfully. Purpose: {payload.get('purpose')}, User ID: {payload.get('sub')}")
            except jwt.ExpiredSignatureError as e:
                logger.error(f"Token expired: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token has expired"
                )
            except jwt.InvalidTokenError as e:
                logger.error(f"Invalid token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid token: {str(e)}"
                )
            
            # Validate token structure
            if payload.get("purpose") != "password_setup":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token purpose"
                )
            
            jti = payload.get("jti")
            user_id = payload.get("sub")
            
            if not jti or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token structure"
                )
            
            # Check JTI in allowlist
            jti_record = await PasswordSetupService.is_setup_jti_valid(jti)
            if not jti_record:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Verify user ID matches
            if jti_record["user_id"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token user mismatch"
                )
            
            # Get user info
            user = await prisma.user.find_unique(where={"id": user_id})
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {
                "user_id": user_id,
                "email": user.email,
                "expires_at": jti_record["expires_at"].isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying setup token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while verifying token"
            )
    
    @staticmethod
    async def setup_password(token: str, new_password: str) -> Dict[str, Any]:
        """Set password using setup token."""
        try:
            # Verify JWT token
            try:
                payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token has expired"
                )
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Validate token structure
            if payload.get("purpose") != "password_setup":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            jti = payload.get("jti")
            user_id = payload.get("sub")
            
            if not jti or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Check JTI in allowlist
            jti_record = await PasswordSetupService.is_setup_jti_valid(jti)
            if not jti_record:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Verify user ID matches
            if jti_record["user_id"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Validate password strength
            if not PasswordSetupService.validate_password_strength(new_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters with uppercase, lowercase, and digit"
                )
            
            # Set new password
            password_set = await PasswordSetupService.set_user_password(user_id, new_password)
            if not password_set:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to set password. Please try again."
                )
            
            # Revoke all user sessions
            await PasswordSetupService.revoke_all_sessions(user_id)
            
            # Mark JTI as used
            await PasswordSetupService.mark_setup_jti_used(jti)
            
            logger.info(f"Password setup successful for user {user_id}")
            
            return create_success_response(
                data={"message": "Password set successfully"},
                message="Password set successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting up password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred. Please try again later."
            )
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Validate password strength requirements."""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        return True

