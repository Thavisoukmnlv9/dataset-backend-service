import asyncio
import logging
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings
from app.modules.auth.services.mail_service import send_verification_email, send_password_reset_otp_email

logger = logging.getLogger(__name__)

REDIS_URL = settings.redis_url

async def send_verification_email_task(ctx, email: str, otp: str) -> bool:
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, send_verification_email, email, otp
        )
        logger.info(f"Verification email task completed for {email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Verification email task failed for {email}: {str(e)}")
        return False


async def send_password_reset_otp_email_task(ctx, email: str, otp: str) -> bool:
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, send_password_reset_otp_email, email, otp
        )
        logger.info(f"Password reset OTP email task completed for {email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Password reset OTP email task failed for {email}: {str(e)}")
        return False

class WorkerSettings:
    functions = [
        send_verification_email_task,
        send_password_reset_otp_email_task,
    ]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 10
    job_timeout = 300  
    keep_result = 3600  
    poll_delay = 1.0  


async def enqueue_verification_email(email: str, otp: str) -> str:
    try:
        redis_pool = await create_pool(WorkerSettings.redis_settings)
        job = await redis_pool.enqueue_job(
            "send_verification_email_task",
            email,
            otp,
            _defer_by=0  
        )
        logger.info(f"Verification email queued for {email}, job ID: {job.job_id}")
        return job.job_id
    except Exception as e:
        logger.error(f"Failed to enqueue verification email for {email}: {str(e)}")
        raise

async def enqueue_password_reset_otp_email(email: str, otp: str) -> str:
    try:
        redis_pool = await create_pool(WorkerSettings.redis_settings)
        job = await redis_pool.enqueue_job(
            "send_password_reset_otp_email_task",
            email,
            otp,
            _defer_by=0  
        )
        logger.info(f"Password reset OTP email queued for {email}, job ID: {job.job_id}")
        return job.job_id
    except Exception as e:
        logger.error(f"Failed to enqueue password reset OTP email for {email}: {str(e)}")
        raise



