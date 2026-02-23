import string
import hashlib
import secrets
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
import logging
from app.prisma import prisma
from app.core.config import settings

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10  # OTP expires in 10 minutes
MAX_ATTEMPTS = 5
RESEND_THROTTLE_SECONDS = 60  # 1 minute throttle for resend


class EnhancedOTPService:
    """Enhanced OTP service with database storage and security features"""
    
    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP."""
        return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt for OTP hashing."""
        return secrets.token_hex(16)
    
    @staticmethod
    def hash_otp(otp: str, salt: str) -> str:
        """Hash OTP with salt using SHA-256."""
        return hashlib.sha256(f"{otp}{salt}".encode()).hexdigest()
    
    @staticmethod
    async def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find user by email address."""
        try:
            user = await prisma.user.find_unique(where={"email": email})
            if user:
                # Check if user is active (no need for account table)
                return {
                    "id": user.id,
                    "email": user.email,
                    "is_active": user.is_active and not user.banned
                }
            return None
        except Exception as e:
            logger.error(f"Error finding user by email {email}: {str(e)}")
            return None
    
    @staticmethod
    async def upsert_otp(
        email: str, 
        otp: str, 
        purpose: str = "password_reset",
        user_id: Optional[str] = None
    ) -> bool:
        """Store or update OTP in database with hashing and salt."""
        try:
            
            # Generate salt and hash OTP
            salt = EnhancedOTPService.generate_salt()
            otp_hash = EnhancedOTPService.hash_otp(otp, salt)
            
            # Calculate expiry time
            expires_at = datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES)
            
            # Check if OTP already exists for this email and purpose
            existing_otp = await prisma.authotp.find_first(
                where={
                    "email": email,
                    "purpose": purpose,
                    "consumed_at": None
                }
            )
            
            if existing_otp:
                # Update existing OTP
                await prisma.authotp.update(
                    where={"id": existing_otp.id},
                    data={
                        "otp_hash": otp_hash,
                        "salt": salt,
                        "attempts": 0,
                        "expires_at": expires_at,
                        "last_sent_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC)
                    }
                )
            else:
                # Create new OTP
                await prisma.authotp.create(
                    data={
                        "user_id": user_id,
                        "email": email,
                        "purpose": purpose,
                        "otp_hash": otp_hash,
                        "salt": salt,
                        "attempts": 0,
                        "max_attempts": MAX_ATTEMPTS,
                        "expires_at": expires_at,
                        "last_sent_at": datetime.now(UTC)
                    }
                )
            
            logger.info(f"OTP stored for email {email}, purpose: {purpose}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OTP for email {email}: {str(e)}")
            return False
    
    @staticmethod
    async def find_active_otp(email: str, purpose: str = "password_reset") -> Optional[Dict[str, Any]]:
        """Find active OTP for email and purpose."""
        try:
            otp_record = await prisma.authotp.find_first(
                where={
                    "email": email,
                    "purpose": purpose,
                    "consumed_at": None,
                    "expires_at": {"gt": datetime.now(UTC)}
                }
            )
            
            if otp_record:
                return {
                    "id": otp_record.id,
                    "user_id": otp_record.user_id,
                    "email": otp_record.email,
                    "purpose": otp_record.purpose,
                    "otp_hash": otp_record.otp_hash,
                    "salt": otp_record.salt,
                    "attempts": otp_record.attempts,
                    "max_attempts": otp_record.max_attempts,
                    "expires_at": otp_record.expires_at,
                    "last_sent_at": otp_record.last_sent_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Error finding active OTP for email {email}: {str(e)}")
            return None
    
    @staticmethod
    async def increment_otp_attempts(otp_id: str) -> bool:
        """Increment OTP attempt count."""
        try:
            await prisma.authotp.update(
                where={"id": otp_id},
                data={
                    "attempts": {"increment": 1},
                    "updated_at": datetime.now(UTC)
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error incrementing OTP attempts for {otp_id}: {str(e)}")
            return False
    
    @staticmethod
    async def consume_otp(otp_id: str) -> bool:
        """Mark OTP as consumed."""
        try:
            await prisma.authotp.update(
                where={"id": otp_id},
                data={
                    "consumed_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC)
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error consuming OTP {otp_id}: {str(e)}")
            return False
    
    @staticmethod
    async def verify_otp(email: str, provided_otp: str, purpose: str = "password_reset") -> Dict[str, Any]:
        """Verify OTP with enhanced security checks."""
        try:
            # Find active OTP
            otp_record = await EnhancedOTPService.find_active_otp(email, purpose)
            if not otp_record:
                return {
                    "success": False,
                    "message": "Invalid or expired OTP"
                }
            
            # Check if max attempts exceeded
            if otp_record["attempts"] >= otp_record["max_attempts"]:
                # Mark as consumed to prevent further attempts
                await EnhancedOTPService.consume_otp(otp_record["id"])
                return {
                    "success": False,
                    "message": "Maximum attempts exceeded. Please request a new OTP."
                }
            
            # Verify OTP
            expected_hash = EnhancedOTPService.hash_otp(provided_otp, otp_record["salt"])
            if expected_hash == otp_record["otp_hash"]:
                # OTP is correct, consume it
                await EnhancedOTPService.consume_otp(otp_record["id"])
                logger.info(f"OTP verified successfully for email {email}")
                return {
                    "success": True,
                    "message": "OTP verified successfully",
                    "user_id": otp_record["user_id"]
                }
            else:
                # Increment attempts
                await EnhancedOTPService.increment_otp_attempts(otp_record["id"])
                remaining_attempts = otp_record["max_attempts"] - otp_record["attempts"] - 1
                return {
                    "success": False,
                    "message": f"Invalid OTP. {remaining_attempts} attempts remaining."
                }
                
        except Exception as e:
            logger.error(f"Failed to verify OTP for email {email}: {str(e)}")
            return {
                "success": False,
                "message": "OTP verification failed"
            }
    
    @staticmethod
    async def can_resend_otp(email: str, purpose: str = "password_reset") -> bool:
        """Check if OTP can be resent (throttle check)."""
        try:
            otp_record = await prisma.authotp.find_first(
                where={
                    "email": email,
                    "purpose": purpose,
                    "consumed_at": None
                }
            )
            
            if not otp_record or not otp_record.last_sent_at:
                return True
            
            # Check if enough time has passed since last send
            time_since_last_send = datetime.now(UTC) - otp_record.last_sent_at
            return time_since_last_send.total_seconds() >= RESEND_THROTTLE_SECONDS
            
        except Exception as e:
            logger.error(f"Error checking resend throttle for email {email}: {str(e)}")
            return False
    
    @staticmethod
    async def cleanup_expired_otps() -> int:
        """Clean up expired OTPs from database."""
        try:
            result = await prisma.authotp.delete_many(
                where={
                    "expires_at": {"lt": datetime.now(UTC)}
                }
            )
            logger.info(f"Cleaned up {result} expired OTPs")
            return result
        except Exception as e:
            logger.error(f"Error cleaning up expired OTPs: {str(e)}")
            return 0
