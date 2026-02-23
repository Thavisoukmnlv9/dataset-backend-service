"""
Auth API routes.

Thin route layer — delegates all business logic to service functions.
No direct DB calls here.
"""
import logging
from fastapi import APIRouter, Depends, Request, Query
from app.api.dependencies import get_current_user, get_current_active_user, get_admin_user
from app.modules.auth.schemas.auth import (
    UserCreate,
    UserLogin,
    EmailOTPVerificationRequest,
    ResendOTPRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AdminChangePasswordRequest,
)
from app.modules.auth.schemas.reset_password import (
    VerifyOTPRequest,
)
from app.modules.auth.schemas.password_setup import (
    VerifySetupTokenRequest,
    SetupPasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Registration ─────────────────────────────────────────────────────────────

@router.post("/register", summary="Register a new user")
async def register(user_data: UserCreate):
    from app.modules.auth.services.register import register_user
    return await register_user(user_data)


@router.post("/verify-email", summary="Verify email with OTP")
async def verify_email(data: EmailOTPVerificationRequest):
    from app.modules.auth.services.register import verify_email_otp
    return await verify_email_otp(data.email, data.otp)


@router.post("/resend-otp", summary="Resend verification OTP")
async def resend_otp(data: ResendOTPRequest):
    from app.modules.auth.services.register import resend_verification_email
    return await resend_verification_email(data.email)


# ── Login / Logout ───────────────────────────────────────────────────────────

@router.post("/login", summary="Login with email and password")
async def login(user_data: UserLogin, request: Request):
    from app.modules.auth.services.login import login_user_email
    return await login_user_email(user_data, request)


@router.post("/vendor/login", summary="Vendor login with email and password")
async def vendor_login(user_data: UserLogin, request: Request):
    from app.modules.auth.services.vendor_login import login_vendor_email
    return await login_vendor_email(user_data, request)


@router.post("/logout", summary="Logout current user")
async def logout(request: Request, current_user=Depends(get_current_active_user)):
    from app.modules.auth.services.logout import logout_user
    return await logout_user(current_user.id, request)


@router.post("/logout/device", summary="Logout from a specific device")
async def logout_device(
    device_info: dict,
    current_user=Depends(get_current_active_user),
):
    from app.modules.auth.services.logout import logout_user_from_device
    return await logout_user_from_device(current_user.id, device_info)


@router.post("/revoke-all", summary="Revoke all sessions (admin)")
async def revoke_all_sessions(
    user_id: str = Query(..., description="User whose sessions to revoke"),
    _admin=Depends(get_admin_user),
):
    from app.modules.auth.services.logout import revoke_all_user_sessions
    return await revoke_all_user_sessions(user_id)


# ── Token Refresh ────────────────────────────────────────────────────────────

@router.post("/refresh", summary="Refresh access token")
async def refresh_token(data: RefreshTokenRequest, request: Request):
    from app.modules.auth.services.refresh import refresh_token_endpoint
    return await refresh_token_endpoint(data, request)


@router.post("/vendor/refresh", summary="Refresh vendor access token")
async def vendor_refresh_token(data: RefreshTokenRequest, request: Request):
    from app.modules.auth.services.vendor_refresh import refresh_vendor_token_endpoint
    return await refresh_vendor_token_endpoint(data, request)


# ── Session ──────────────────────────────────────────────────────────────────

@router.get("/session", summary="Get current user session info")
async def get_session(current_user=Depends(get_current_active_user)):
    from app.modules.auth.services.get_session import get_session as _get_session
    return await _get_session(current_user.id)


# ── Password Reset ───────────────────────────────────────────────────────────

@router.post("/forgot-password", summary="Request password reset OTP")
async def forgot_password(data: ForgotPasswordRequest, request: Request):
    from app.modules.auth.services.reset_password_service import ResetPasswordService
    ip = request.client.host if request.client else "unknown"
    return await ResetPasswordService.forgot_password(data.email, ip)


@router.post("/verify-reset-otp", summary="Verify password-reset OTP and get reset token")
async def verify_reset_otp(data: VerifyOTPRequest, request: Request):
    from app.modules.auth.services.reset_password_service import ResetPasswordService
    ip = request.client.host if request.client else "unknown"
    return await ResetPasswordService.verify_otp(data.email, data.otp, ip)


@router.post("/reset-password", summary="Reset password with reset token")
async def reset_password(data: ResetPasswordRequest, request: Request):
    from app.modules.auth.services.reset_password_service import ResetPasswordService
    ip = request.client.host if request.client else "unknown"
    return await ResetPasswordService.reset_password(data.token, data.new_password, ip)


@router.post(
    "/admin/change-password",
    summary="Admin: change any user's password",
)
async def admin_change_password(
    data: AdminChangePasswordRequest,
    admin_user=Depends(get_admin_user),
):
    from app.modules.auth.services.reset_password_service import ResetPasswordService
    return await ResetPasswordService.admin_change_user_password(
        data.user_id, data.new_password, admin_user.id
    )


# ── Password Setup (Vendor Onboarding) ──────────────────────────────────────

@router.post("/setup/verify-token", summary="Verify vendor password-setup token")
async def verify_setup_token(data: VerifySetupTokenRequest):
    from app.modules.auth.services.password_setup_service import PasswordSetupService
    return await PasswordSetupService.verify_setup_token(data.token)


@router.post("/setup/password", summary="Set password via setup token")
async def setup_password(data: SetupPasswordRequest):
    from app.modules.auth.services.password_setup_service import PasswordSetupService
    return await PasswordSetupService.setup_password(data.token, data.new_password)
