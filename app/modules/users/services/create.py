"""Service for creating users"""
from typing import Dict, Any, Optional
from fastapi import HTTPException, status, UploadFile
from app.prisma import prisma
from app.modules.users.schemas.user import (
    UserResponse,
    UserFormDataCreate,
)
from app.shared.utils.responses.response import create_success_response
from app.shared.services.infrastructure.storage import storage_service
from app.core.security import hash_password


async def create_user_with_form_data_and_image(
    user_data: UserFormDataCreate,
    avatar_file: Optional[UploadFile] = None,
    current_user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new user with FormData including user roles and image upload using transaction"""
    try:
        avatar_url = None
        if avatar_file:
            image_upload_result = await storage_service.upload_file(avatar_file, "users")
            if image_upload_result.success:
                avatar_url = image_upload_result.data["object_name"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload profile image"
                )
        user_data.avatar_url = avatar_url

        # Use Prisma transaction to ensure all operations succeed or fail together
        async with prisma.tx() as tx:
            # Check if user with email already exists
            existing_user = await tx.user.find_unique(where={"email": user_data.email})
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )

            # Check if user with phone number already exists (if provided)
            if user_data.phone_number:
                existing_phone_users = await tx.user.find_many(
                    where={"phone_number": user_data.phone_number}
                )
                if existing_phone_users:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="User with this phone number already exists"
                    )


            # Hash password if provided
            hashed_password = None
            if user_data.password:
                hashed_password = hash_password(user_data.password)

            # Create user with all fields
            user = await tx.user.create(
                data={
                    "email": user_data.email,
                    "password": hashed_password,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "nickname": f"{user_data.first_name} {user_data.last_name}".strip() if user_data.first_name and user_data.last_name else None,
                    "phone_number": user_data.phone_number,
                    "avatar_url": user_data.avatar_url,
                    "role": user_data.role.value if user_data.role else "STAFF",
                    "banned": False,
                    "ban_reason": None,
                    "ban_expires": None,
                    "is_anonymous": user_data.is_anonymous,
                    "email_verified": user_data.email_verified,
                    "phone_number_verified": user_data.phone_number_verified,
                    "last_login_at": user_data.last_login_at,
                    "login_count": user_data.login_count,
                    "is_active": True,
                }
            )

            # Create user roles if provided
            created_user_roles = []
            if user_data.user_roles:
                for role_data in user_data.user_roles:
                    role = await tx.rbacrole.find_unique(where={"id": role_data.role_id})
                    if not role:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Role with ID {role_data.role_id} not found"
                        )
                    
                    user_role = await tx.rbacuserrole.create(
                        data={
                            "user_id": str(user.id),
                            "role_id": role_data.role_id,
                            "assigned_by": current_user_id,
                            "expires_at": None,
                            "is_active": True,
                        }
                    )
                    created_user_roles.append(user_role)

            # Get the created user with all relations
            created_user = await tx.user.find_unique(
                where={"id": str(user.id)},
                include={
                    "profile": True,
                    "tourist": True,
                    "vendor": {
                        "include": {
                            "business": True
                        }
                    },
                    "wallet": True,
                    "user_roles": {
                        "include": {
                            "role": True
                        }
                    }
                }
            )

            result = {
                "user": created_user,
                "user_roles": created_user_roles
            }

        # Generate presigned URL for the profile image if it exists
        profile_image_url = None
        if result["user"].avatar_url:
            object_name = storage_service.extract_object_name_from_url(result["user"].avatar_url)
            if object_name:
                # Generate presigned URL for the profile image
                image_urls = await storage_service.get_presigned_urls_for_file([object_name])
                profile_image_url = image_urls[0] if image_urls and image_urls[0] else None

        # Update the user response with the presigned URL
        user_response_data = result["user"].model_dump()
        user_response_data["avatar_url"] = profile_image_url

        return create_success_response(
            message="User created successfully with roles and profile image",
            data={
                "user": UserResponse.model_validate(user_response_data),
                "user_roles": result["user_roles"]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        # Handle specific database constraint errors
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
        elif "Unique constraint failed on the fields: (`provider_id`, `account_id`)" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this provider and account ID combination already exists. Please use different account details."
            )
        elif "Unique constraint failed" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this information already exists. Please check your details and try again."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating user: {error_message}"
            )
