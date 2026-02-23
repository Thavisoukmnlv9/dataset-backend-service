"""Service for user lookup functionality"""
from typing import Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from app.prisma import prisma
from app.modules.users.schemas.user import UserLookupItem, UserLookupQueryDTO


async def lookup_users(query: UserLookupQueryDTO) -> Dict[str, Any]:
    """Lookup users with search and pagination"""
    try:
        
        where_clause = {}
        if query.q:
            where_clause["OR"] = [
                {"email": {"contains": query.q, "mode": "insensitive"}},
                {"phone_number": {"contains": query.q, "mode": "insensitive"}},
                {"first_name": {"contains": query.q, "mode": "insensitive"}},
                {"last_name": {"contains": query.q, "mode": "insensitive"}},
                {"nickname": {"contains": query.q, "mode": "insensitive"}}
            ]
        where_clause["banned"] = False
        where_clause["deleted_at"] = None
        where_clause["is_active"] = True

        users = await prisma.user.find_many(
            where=where_clause,
            order={"email": "asc"},
            skip=query.skip,
            take=query.limit
        )

        total_count = await prisma.user.count(where=where_clause)

        items = []
        for user in users:
            display_name = user.email
            
            # Use user's own name fields first
            if user.first_name or user.last_name:
                name_parts = []
                if user.first_name:
                    name_parts.append(user.first_name)
                if user.last_name:
                    name_parts.append(user.last_name)
                if name_parts:
                    display_name = " ".join(name_parts)
            elif user.nickname:
                display_name = user.nickname

            if user.role:
                display_name = f"{display_name} ({user.role})"

            items.append(UserLookupItem(
                id=str(user.id),
                name=display_name
            ))

        return {
            "success": True,
            "data": {
                "items": [item.model_dump() for item in items],
                "total": total_count
            },
            "message": "Users lookup successful"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up users: {str(e)}"
        )

async def lookup_user_by_id(user_id: str) -> Dict[str, Any]:
    """Lookup a specific user by ID"""
    try:
        
        try:
            uuid_user_id = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        user = await prisma.user.find_unique(
            where={"id": str(uuid_user_id)}
        )

        if not user:
            return {"success": True, "data": {"item": None}, "message": "User not found"}

        if user.banned or user.deleted_at is not None or not user.is_active:
            return {"success": True, "data": {"item": None}, "message": "User not found"}

        display_name = user.email

        # Use user's own name fields first
        if user.first_name or user.last_name:
            name_parts = []
            if user.first_name:
                name_parts.append(user.first_name)
            if user.last_name:
                name_parts.append(user.last_name)
            if name_parts:
                display_name = " ".join(name_parts)
        elif user.nickname:
            display_name = user.nickname

        if user.role:
            display_name = f"{display_name} ({user.role})"

        item = UserLookupItem(
            id=str(user.id),
            name=display_name
        )

        return {"success": True, "data": {"item": item.model_dump()}, "message": "User found successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up user: {str(e)}"
        )