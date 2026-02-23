import jwt
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional
import logging
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.prisma import prisma
from app.modules.auth.services.otp_service_enhanced import EnhancedOTPService
from app.modules.auth.services.rate_limit_service import RateLimitService
from app.shared.utils.responses.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)

# JWT settings for reset tokens
RESET_TOKEN_EXPIRE_MINUTES = 15
JWT_ALGORITHM = "HS256"


class ResetPasswordService:
    """Service for handling password reset operations"""
    
    @staticmethod
    async def store_reset_jti(jti: str, user_id: str, expires_at: datetime) -> bool:
        """Store reset token JTI in allowlist."""
        try:
            await prisma.authresettoken.create(
                data={
                    "jti": jti,
                    "user_id": user_id,
                    "purpose": "password_reset",
                    "expires_at": expires_at
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error storing reset JTI {jti}: {str(e)}")
            return False
    
    @staticmethod
    async def is_reset_jti_valid(jti: str) -> Optional[Dict[str, Any]]:
        """Check if reset JTI is valid and not used."""
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
            
            return {
                "jti": token_record.jti,
                "user_id": token_record.user_id,
                "purpose": token_record.purpose,
                "expires_at": token_record.expires_at,
                "created_at": token_record.created_at
            }
            
        except Exception as e:
            logger.error(f"Error checking reset JTI {jti}: {str(e)}")
            return None
    
    @staticmethod
    async def mark_reset_jti_used(jti: str) -> bool:
        """Mark reset JTI as used."""
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
            
            logger.info(f"Password updated for user {user_id}")
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
    async def forgot_password(email: str, ip_address: str) -> Dict[str, Any]:
        """Initiate forgot password flow with OTP."""
        try:
            # Check rate limit
            identifier = RateLimitService.get_identifier(ip_address, email)
            rate_limit = await RateLimitService.check_rate_limit(
                identifier, "forgot_password", ip_address
            )
            
            if not rate_limit["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
            
            # Check if user exists
            user = await EnhancedOTPService.find_user_by_email(email)
            if not user:
                # Return generic message for security
                return create_success_response(
                    data={"message": "If the email exists, a reset link has been sent"},
                    message="If the email exists, a reset link has been sent"
                )
            
            # Check if user is active
            if not user["is_active"]:
                return create_success_response(
                    data={"message": "If the email exists, a reset link has been sent"},
                    message="If the email exists, a reset link has been sent"
                )
            
            # Check if OTP can be resent
            can_resend = await EnhancedOTPService.can_resend_otp(email, "password_reset")
            if not can_resend:
                return create_success_response(
                    data={"message": "If the email exists, a reset link has been sent"},
                    message="If the email exists, a reset link has been sent"
                )
            
            # Generate and store OTP
            otp = EnhancedOTPService.generate_otp()
            otp_stored = await EnhancedOTPService.upsert_otp(
                email, otp, "password_reset", user["id"]
            )
            
            if not otp_stored:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate reset code. Please try again."
                )
            
            # Send OTP email via worker
            try:
                from app.core.worker import enqueue_password_reset_otp_email
                job_id = await enqueue_password_reset_otp_email(email, otp)
                logger.info(f"Password reset OTP email queued for {email}, job ID: {job_id}")
            except Exception as e:
                logger.error(f"Failed to queue password reset email for {email}: {str(e)}")
                # Don't fail the request if email fails
            
            return create_success_response(
                data={"message": "If the email exists, a reset link has been sent"},
                message="If the email exists, a reset link has been sent"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in forgot password for {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred. Please try again later."
            )
    
    @staticmethod
    async def verify_otp(email: str, otp: str, ip_address: str) -> Dict[str, Any]:
        """Verify OTP and issue reset token."""
        try:
            # Check rate limit
            identifier = RateLimitService.get_identifier(ip_address, email)
            rate_limit = await RateLimitService.check_rate_limit(
                identifier, "verify_otp", ip_address
            )
            
            if not rate_limit["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
            
            # Verify OTP
            otp_result = await EnhancedOTPService.verify_otp(email, otp, "password_reset")
            
            if not otp_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=otp_result["message"]
                )
            
            # Generate reset token
            jti = str(uuid.uuid4())
            expires_at = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
            
            # Create JWT token
            token_data = {
                "sub": otp_result["user_id"],
                "purpose": "password_reset",
                "jti": jti,
                "iat": datetime.now(UTC).timestamp(),
                "exp": expires_at.timestamp()
            }
            
            reset_token = jwt.encode(token_data, settings.jwt_secret, algorithm=JWT_ALGORITHM)
            
            # Store JTI in allowlist
            jti_stored = await ResetPasswordService.store_reset_jti(
                jti, otp_result["user_id"], expires_at
            )
            
            if not jti_stored:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate reset token. Please try again."
                )
            
            return create_success_response(
                data={
                    "resetToken": reset_token,
                    "expiresAt": expires_at.isoformat()
                },
                message="OTP verified successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred. Please try again later."
            )
    
    @staticmethod
    async def reset_password(
        reset_token: str, 
        new_password: str, 
        ip_address: str
    ) -> Dict[str, Any]:
        """Reset password using reset token."""
        try:
            # Check rate limit
            identifier = RateLimitService.get_identifier(ip_address)
            rate_limit = await RateLimitService.check_rate_limit(
                identifier, "reset_password", ip_address
            )
            
            if not rate_limit["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
            
            # Verify JWT token
            try:
                payload = jwt.decode(reset_token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token"
                )
            
            # Validate token structure
            if payload.get("purpose") != "password_reset":
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
            jti_record = await ResetPasswordService.is_reset_jti_valid(jti)
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
            if not ResetPasswordService.validate_password_strength(new_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters with uppercase, lowercase, and digit"
                )
            
            # Set new password
            password_set = await ResetPasswordService.set_user_password(user_id, new_password)
            if not password_set:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password. Please try again."
                )
            
            # Revoke all user sessions
            await ResetPasswordService.revoke_all_sessions(user_id)
            
            # Mark JTI as used
            await ResetPasswordService.mark_reset_jti_used(jti)
            
            logger.info(f"Password reset successful for user {user_id}")
            
            return create_success_response(
                data={"message": "Password reset successful"},
                message="Password reset successful"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
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
    
    @staticmethod
    async def admin_change_user_password(
        user_id: str,
        new_password: str,
        admin_user_id: str
    ) -> Dict[str, Any]:
        """Admin function to change any user's password."""
        try:
            # Validate password strength
            if not ResetPasswordService.validate_password_strength(new_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters with uppercase, lowercase, and digit"
                )
            
            # Check if target user exists
            target_user = await prisma.user.find_unique(where={"id": user_id})
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Set new password
            password_set = await ResetPasswordService.set_user_password(user_id, new_password)
            if not password_set:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password. Please try again."
                )
            
            # Revoke all user sessions for security
            await ResetPasswordService.revoke_all_sessions(user_id)
            
            logger.info(f"Admin {admin_user_id} changed password for user {user_id}")
            
            return create_success_response(
                data={
                    "message": "Password changed successfully",
                    "user_id": user_id,
                    "email": target_user.email
                },
                message="Password changed successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in admin password change for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred. Please try again later."
            )