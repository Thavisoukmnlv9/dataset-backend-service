from typing import Dict, Any
from datetime import datetime, UTC
from fastapi import HTTPException, status, Request
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response, create_error_response


class LogoutService:
    @staticmethod
    async def logout_user(user_id: str, request: Request = None) -> Dict[str, Any]:
        """Logout user and revoke all refresh tokens and sessions"""
        try:
            # Verify user exists
            user = await prisma.user.find_unique(where={"id": user_id})
            if not user:
                return create_error_response(
                    error_code="USER_NOT_FOUND",
                    message="User not found"
                )

            # Revoke all active refresh tokens for the user
            await prisma.refreshtoken.update_many(
                where={
                    "user_id": user_id,
                    "is_revoked": False
                },
                data={
                    "is_revoked": True,
                    "revoked_at": datetime.now(UTC)
                }
            )

            # Deactivate all active sessions for the user
            await prisma.session.update_many(
                where={
                    "user_id": user_id,
                    "is_active": True
                },
                data={
                    "is_active": False
                }
            )

            # Update user's last logout time
            await prisma.user.update(
                where={"id": user_id},
                data={"last_logout_at": datetime.now(UTC)}
            )

            return create_success_response(
                data={
                    "user_id": user_id,
                    "logout_time": datetime.now(UTC).isoformat(),
                    "message": "Logout successful"
                },
                message="User logged out successfully"
            )

        except Exception as e:
            return create_error_response(
                error_code="LOGOUT_FAILED",
                message=f"Logout failed: {str(e)}"
            )

    @staticmethod
    async def logout_user_from_device(user_id: str, device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Logout user from specific device/session"""
        try:
            # Find and deactivate specific session based on device info
            if device_info:
                session = await prisma.session.find_first(
                    where={
                        "user_id": user_id,
                        "is_active": True,
                        "ip_address": device_info.get("ip_address"),
                        "user_agent": device_info.get("user_agent")
                    }
                )
                
                if session:
                    await prisma.session.update(
                        where={"id": session.id},
                        data={
                            "is_active": False
                        }
                    )

            return create_success_response(
                data={
                    "user_id": user_id,
                    "logout_time": datetime.now(UTC).isoformat(),
                    "message": "Device logout successful"
                },
                message="User logged out from device successfully"
            )

        except Exception as e:
            return create_error_response(
                error_code="DEVICE_LOGOUT_FAILED",
                message=f"Device logout failed: {str(e)}"
            )

    @staticmethod
    async def revoke_all_user_sessions(user_id: str) -> Dict[str, Any]:
        """Revoke all sessions and tokens for a user (admin function)"""
        try:
            # Revoke all refresh tokens
            revoked_tokens = await prisma.refreshtoken.update_many(
                where={
                    "user_id": user_id,
                    "is_revoked": False
                },
                data={
                    "is_revoked": True,
                    "revoked_at": datetime.now(UTC)
                }
            )

            # Deactivate all sessions
            deactivated_sessions = await prisma.session.update_many(
                where={
                    "user_id": user_id,
                    "is_active": True
                },
                data={
                    "is_active": False
                }
            )

            return create_success_response(
                data={
                    "user_id": user_id,
                    "revoked_tokens_count": revoked_tokens.count if hasattr(revoked_tokens, 'count') else 0,
                    "deactivated_sessions_count": deactivated_sessions.count if hasattr(deactivated_sessions, 'count') else 0,
                    "revoke_time": datetime.now(UTC).isoformat()
                },
                message="All user sessions and tokens revoked successfully"
            )

        except Exception as e:
            return create_error_response(
                error_code="REVOKE_ALL_FAILED",
                message=f"Failed to revoke all sessions: {str(e)}"
            )


async def logout_user(user_id: str, request: Request = None) -> Dict[str, Any]:
    """Main logout function - logout user and revoke all tokens/sessions"""
    try:
        result = await LogoutService.logout_user(user_id, request)
        
        if not result.success:
            if hasattr(result, 'error'):
                error_code = result.error.get("code", "LOGOUT_FAILED")
                error_message = result.error.get("message", "Logout failed")
                status_code = status.HTTP_400_BAD_REQUEST
                
                if error_code == "USER_NOT_FOUND":
                    status_code = status.HTTP_404_NOT_FOUND
                elif error_code == "LOGOUT_FAILED":
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Logout failed"
                )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging out user: {error_message}"
        )

async def logout_user_from_device(user_id: str, device_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Logout user from specific device"""
    try:
        result = await LogoutService.logout_user_from_device(user_id, device_info)
        
        if not result.success:
            if hasattr(result, 'error'):
                error_code = result.error.get("code", "DEVICE_LOGOUT_FAILED")
                error_message = result.error.get("message", "Device logout failed")
                status_code = status.HTTP_400_BAD_REQUEST
                
                if error_code == "DEVICE_LOGOUT_FAILED":
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Device logout failed"
                )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging out user from device: {error_message}"
        )

async def revoke_all_user_sessions(user_id: str) -> Dict[str, Any]:
    """Admin function to revoke all user sessions and tokens"""
    try:
        result = await LogoutService.revoke_all_user_sessions(user_id)
        
        if not result.success:
            if hasattr(result, 'error'):
                error_code = result.error.get("code", "REVOKE_ALL_FAILED")
                error_message = result.error.get("message", "Failed to revoke all sessions")
                status_code = status.HTTP_400_BAD_REQUEST
                
                if error_code == "REVOKE_ALL_FAILED":
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to revoke all sessions"
                )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error revoking all user sessions: {error_message}"
        )