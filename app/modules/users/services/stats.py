"""Service for user statistics and analytics"""
from typing import Dict, Any
from datetime import UTC, datetime, timedelta
from fastapi import HTTPException, status
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response


async def get_user_stats() -> Dict[str, Any]:
    """Get user statistics and analytics"""
    

    try:
        # Get total users count
        total_users = await prisma.user.count()
        
        # Get active users (not banned, not deleted, is_active)
        active_users = await prisma.user.count(
            where={
                "banned": False,
                "deleted_at": None,
                "is_active": True
            }
        )
        
        # Get banned users
        banned_users = await prisma.user.count(
            where={
                "banned": True,
                "deleted_at": None
            }
        )
        
        # Get verified users (email verified)
        verified_users = await prisma.user.count(
            where={
                "email_verified": True,
                "deleted_at": None
            }
        )
        
        # Get anonymous users
        anonymous_users = await prisma.user.count(
            where={
                "is_anonymous": True,
                "deleted_at": None
            }
        )
        
        # Get users by role
        users_by_role = {}
        users = await prisma.user.find_many(
            where={"deleted_at": None}
        )
        
        for user in users:
            role = user.role or "no_role"
            users_by_role[role] = users_by_role.get(role, 0) + 1
        
        # Get recent registrations (last 30 days)
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        recent_registrations = await prisma.user.count(
            where={
                "created_at": {"gte": thirty_days_ago},
                "deleted_at": None
            }
        )
        
        # Get recent logins (last 7 days)
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        recent_logins = await prisma.user.count(
            where={
                "last_login_at": {"gte": seven_days_ago},
                "deleted_at": None
            }
        )
        
        # Get daily registrations for the last 30 days
        daily_registrations = []
        for i in range(30):
            date = datetime.now(UTC) - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            count = await prisma.user.count(
                where={
                    "created_at": {
                        "gte": start_of_day,
                        "lte": end_of_day
                    },
                    "deleted_at": None
                }
            )
            
            daily_registrations.append({
                "date": start_of_day.date().isoformat(),
                "count": count
            })
        
        # Get role distribution
        role_distribution = []
        for role, count in users_by_role.items():
            percentage = (count / total_users * 100) if total_users > 0 else 0
            role_distribution.append({
                "role": role,
                "count": count,
                "percentage": round(percentage, 2)
            })
        
        # Get verification status
        email_verified_count = await prisma.user.count(
            where={
                "email_verified": True,
                "deleted_at": None
            }
        )
        
        phone_verified_count = await prisma.user.count(
            where={
                "phone_number_verified": True,
                "deleted_at": None
            }
        )
        
        verification_stats = {
            "email_verified": {
                "count": email_verified_count,
                "percentage": round((email_verified_count / total_users * 100) if total_users > 0 else 0, 2)
            },
        }
        
        stats_data = {
            "total_users": total_users,
            "active_users": active_users,
            "banned_users": banned_users,
            "verified_users": verified_users,
            "anonymous_users": anonymous_users,
            "users_by_role": users_by_role,
            "recent_registrations": recent_registrations,
            "recent_logins": recent_logins,
            "daily_registrations": daily_registrations,
            "role_distribution": role_distribution,
            "verification_stats": verification_stats,
        }

        return create_success_response(
            message="User statistics retrieved successfully",
            data={"item": stats_data}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user statistics: {str(e)}"
        )
