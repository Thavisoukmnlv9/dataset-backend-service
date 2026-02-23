"""Service for updating users"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from app.prisma import prisma
from app.modules.users.schemas.user import UserRoleEnum, UserUpdate, UserResponse, UserBanUpdate
from app.shared.utils.responses.response import create_success_response
from app.shared.services.infrastructure.storage import storage_service
from app.shared.exceptions import raise_business_logic_error, raise_not_found_error


async def update_user(user_id: UUID,  user_data: UserUpdate, avatar_file: Optional[UploadFile] = None) -> Dict[str, Any]:
    """Update a user"""
    try:
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise_not_found_error(message="User not found")

        new_avatar_url = None
        if avatar_file:
            if existing_user.avatar_url:
                avatar_path = storage_service.extract_object_name_from_url(
                    existing_user.avatar_url)
                await storage_service.move_delete_file(avatar_path, "deleted-users")

            image_upload_result = await storage_service.upload_file(avatar_file, "users")
            if image_upload_result.success:
                new_avatar_url = image_upload_result.data["object_name"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload profile image"
                )

        if new_avatar_url:
            user_data.avatar_url = new_avatar_url

        if user_data.email and user_data.email != existing_user.email:
            email_user = await prisma.user.find_unique(where={"email": user_data.email})
            if email_user and email_user.id != existing_user.id:
                raise_business_logic_error(
                    error_code="BAD_REQUEST",
                    message="User with this email already exists",
                    status_code=400,
                    fields=[{
                        "field": "body -> email",
                        "location": "body",
                        "type": "conflict",
                        "message": "User with this email already exists"
                    }]
                )

        if user_data.phone_number and user_data.phone_number != existing_user.phone_number:
            phone_user = await prisma.user.find_first(where={"phone_number": user_data.phone_number})
            if phone_user and phone_user.id != existing_user.id:
                raise_business_logic_error(
                    error_code="BAD_REQUEST",
                    message="User with this phone number already exists",
                    status_code=400,
                    fields=[{
                        "field": "body -> phone_number",
                        "location": "body",
                        "type": "conflict",
                        "message": "User with this phone number already exists"
                    }]
                )
        update_data = {}
        if user_data.email is not None:
            update_data["email"] = user_data.email
        if user_data.first_name is not None:
            update_data["first_name"] = user_data.first_name
        if user_data.last_name is not None:
            update_data["last_name"] = user_data.last_name
        if user_data.nickname is not None:
            update_data["nickname"] = user_data.nickname
        if user_data.phone_number is not None:
            update_data["phone_number"] = user_data.phone_number
        if user_data.country_code is not None:
            update_data["country_code"] = user_data.country_code
        if user_data.avatar_url is not None:
            update_data["avatar_url"] = user_data.avatar_url
        if user_data.language_pref is not None:
            update_data["language_pref"] = user_data.language_pref
        if user_data.theme_pref is not None:
            update_data["theme_pref"] = user_data.theme_pref
        if user_data.role is not None:
            update_data["role"] = UserRoleEnum(user_data.role)
        if user_data.is_anonymous is not None:
            update_data["is_anonymous"] = user_data.is_anonymous
        if user_data.is_active is not None:
            update_data["is_active"] = user_data.is_active

        user = await prisma.user.update(
            where={"id": str(user_id)},
            data=update_data,
        )

        # Filter response to only include specified fields
        user_dict = UserResponse.model_validate(user).model_dump()
        filtered_data = {
            "email": user_dict.get("email"),
            "first_name": user_dict.get("first_name"),
            "last_name": user_dict.get("last_name"),
            "nickname": user_dict.get("nickname"),
            "country_code": user_dict.get("country_code"),
            "avatar_url": user_dict.get("avatar_url"),
            "language_pref": user_dict.get("language_pref"),
            "email_verified": user_dict.get("email_verified"),
            "email_verified_at": user_dict.get("email_verified_at"),
            "phone_number_verified": user_dict.get("phone_number_verified"),
            "phone_number": user_dict.get("phone_number"),
            "theme_pref": user_dict.get("theme_pref"),
            "role": user_dict.get("role"),
            "banned": user_dict.get("banned"),
            "is_anonymous": user_dict.get("is_anonymous"),
            "is_active": user_dict.get("is_active"),
            "id": user_dict.get("id"),
            "updated_at": user_dict.get("updated_at")
        }

        return create_success_response(
            message="User updated successfully",
            data=filtered_data
        )

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        if "Unique constraint failed on the fields: (`email`)" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists. Please use a different email address."
            )
        elif "Unique constraint failed on the fields: (`phone_number`)" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this phone number already exists. Please use a different phone number."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update user: {error_message}"
            )


async def ban_user(user_id: UUID, ban_data: UserBanUpdate) -> Dict[str, Any]:
    """Ban or unban a user"""

    try:
        # Check if user exists
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prepare ban update data
        update_data = {
            "banned": ban_data.banned,
            "ban_reason": ban_data.ban_reason if ban_data.banned else None,
            "ban_expires": ban_data.ban_expires if ban_data.banned else None
        }

        # Update user ban status
        user = await prisma.user.update(
            where={"id": str(user_id)},
            data=update_data,
        )

        action = "banned" if ban_data.banned else "unbanned"
        return create_success_response(
            message=f"User {action} successfully",
            data=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user ban status: {str(e)}"
        )


async def verify_user_email(user_id: UUID) -> Dict[str, Any]:
    """Verify user email"""

    try:
        # Check if user exists
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update email verification status
        user = await prisma.user.update(
            where={"id": str(user_id)},
            data={"email_verified": True},
        )

        return create_success_response(
            message="User email verified successfully",
            data=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify user email: {str(e)}"
        )


async def verify_user_phone(user_id: UUID) -> Dict[str, Any]:
    """Verify user phone number"""

    try:
        # Check if user exists
        existing_user = await prisma.user.find_unique(where={"id": str(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update phone verification status
        user = await prisma.user.update(
            where={"id": str(user_id)},
            data={"phone_number_verified": True},
        )

        return create_success_response(
            message="User phone number verified successfully",
            data=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify user phone number: {str(e)}"
        )
