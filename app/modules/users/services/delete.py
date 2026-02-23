"""Service for deleting users"""
from typing import Dict, Any
from uuid import UUID
from datetime import UTC, datetime
from fastapi import HTTPException, status
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response


async def delete_user(user_id: UUID) -> Dict[str, Any]:
    """Soft delete a user"""
    

    try:
        # Check if user exists
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if user is already deleted
        if existing_user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already deleted"
            )

        # Soft delete user
        await prisma.user.update(
            where={"id": str(user_id)}, 
            data={"deleted_at": datetime.now(UTC)}
        )

        return create_success_response(
            message="User deleted successfully",
            data=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


async def restore_user(user_id: UUID) -> Dict[str, Any]:
    """Restore a soft-deleted user"""
    

    try:
        # Check if user exists
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if user is not deleted
        if not existing_user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not deleted"
            )

        # Restore user
        await prisma.user.update(
            where={"id": str(user_id)}, 
            data={"deleted_at": None}
        )

        return create_success_response(
            message="User restored successfully",
            data=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore user: {str(e)}"
        )


async def hard_delete_user(user_id: UUID) -> Dict[str, Any]:
    """Permanently delete a user (admin only)"""
    

    try:
        # Check if user exists
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Hard delete user (this will cascade delete related records)
        await prisma.user.delete(where={"id": str(user_id)})

        return create_success_response(
            message="User permanently deleted successfully",
            data=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to permanently delete user: {str(e)}"
        )
