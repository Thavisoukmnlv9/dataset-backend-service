from fastapi import HTTPException, status
from app.prisma import prisma
from app.core.security import hash_password
from app.core.worker import enqueue_verification_email
from app.modules.auth.schemas.user_create import UserCreate
from app.modules.auth.services.otp_service_enhanced import EnhancedOTPService
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def register_user(user_data: UserCreate) -> Dict[str, Any]:
    try:
        existing_user = await prisma.user.find_unique(
            where={"email": user_data.email}
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        hashed_password = hash_password(user_data.password)
        
        # Create full name from first and last name
        nickname = f"{user_data.first_name} {user_data.last_name}".strip()
        
        user = await prisma.user.create(
            data={
                "email": user_data.email,
                "password": hashed_password,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "nickname": nickname,
                "phone_number": user_data.phone_number,
                "country_code": user_data.country_code,
                "language_pref": user_data.language_pref,
                "theme_pref": user_data.theme_pref,
                "email_verified": False,
                "role": "tourist",  # Default role
                "is_active": True
            }
        )
        otp = EnhancedOTPService.generate_otp()
        otp_stored = await EnhancedOTPService.upsert_otp(
            email=user.email,
            otp=otp,
            purpose="email_verification",
            user_id=user.id
        )
        
        if not otp_stored:
            logger.error(f"Failed to store OTP for email {user.email}")
        try:
            job_id = await enqueue_verification_email(user.email, otp)
            logger.info(f"OTP email queued for email {user.email}, job ID: {job_id}")
        except Exception as e:
            logger.error(f"Failed to queue OTP email for email {user.email}: {str(e)}")
        
        return {
            "message": "Registration successful. OTP sent to your email.",
            "email": user.email,
            "email_verified": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed for email {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


async def resend_verification_email(email: str) -> Dict[str, Any]:
    try:
        user = await prisma.user.find_unique(where={"email": email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Check if OTP can be resent
        can_resend = await EnhancedOTPService.can_resend_otp(email, "email_verification")
        if not can_resend:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait before requesting another OTP"
            )
        
        # Generate and store new OTP using EnhancedOTPService
        otp = EnhancedOTPService.generate_otp()
        otp_stored = await EnhancedOTPService.upsert_otp(
            email=user.email,
            otp=otp,
            purpose="email_verification",
            user_id=user.id
        )
        
        if not otp_stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP. Please try again."
            )
        
        try:
            job_id = await enqueue_verification_email(user.email, otp)
            logger.info(f"Verification OTP email resent for user {user.id}, job ID: {job_id}")
        except Exception as e:
            logger.error(f"Failed to queue verification email for user {user.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please try again."
            )
        
        return {
            "message": "Verification OTP sent successfully. Please check your email.",
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification email failed for {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email. Please try again."
        )


async def verify_email_otp(email: str, otp: str) -> Dict[str, Any]:
    """
    Verify email using OTP instead of token-based verification.
    This function is used by the verify_otp_endpoint in routes.py
    """
    try:
        
        # Verify OTP using EnhancedOTPService
        otp_result = await EnhancedOTPService.verify_otp(email, otp, "email_verification")
        
        if not otp_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"]
            )
        
        # Update user email_verified status
        user = await prisma.user.update(
            where={"email": email},
            data={"email_verified": True}
        )
        
        logger.info(f"Email verified successfully for user {user.id}")
        return {
            "message": "Email verified successfully",
            "user_id": user.id,
            "email": user.email,
            "email_verified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed. Please try again."
        )