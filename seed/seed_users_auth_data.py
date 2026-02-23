#!/usr/bin/env python3
"""
Seed script for users authentication data.
Creates 5 sample users covering different roles and types.
"""

from app.prisma import prisma, connect_db, disconnect_db
from app.core.security import hash_password
from app.shared.services.infrastructure.storage import storage_service
import asyncio
import sys
import os
from datetime import datetime, timedelta, UTC
from fastapi import UploadFile
import io

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


USERS_AUTH_DATA = [
    {
        "email": "admin@dataset.com",
        "password": "admin123456",
        "first_name": "Admin",
        "last_name": "User",
        "nickname": None,
        "phone_number": "+85620123456789",
        "country_code": "LAO",
        "language_pref": "en",
        "role": "SUPER_ADMIN",
        "email_verified": True,
        "phone_number_verified": True,
        "banned": False,
        "is_anonymous": False,
        "last_login_at": datetime.now(UTC) - timedelta(hours=1),
        "login_count": 25,
    },
    {
        "email": "platform.admin@dataset.com",
        "password": "platform123456",
        "first_name": "Platform",
        "last_name": "Administrator",
        "nickname": "Admin",
        "phone_number": "+85620123456787",
        "country_code": "LAO",
        "language_pref": "en",
        "role": "ADMIN",
        "email_verified": True,
        "phone_number_verified": True,
        "banned": False,
        "is_anonymous": False,
        "last_login_at": datetime.now(UTC) - timedelta(hours=3),
        "login_count": 20,
    },
    {
        "email": "pilot@laoairlines.com",
        "password": "admin123456",
        "first_name": "Bounmy",
        "last_name": "Sisouphanh",
        "nickname": None,
        "phone_number": "+85620123456791",
        "country_code": "LAO",
        "language_pref": "lo",
        "role": "ADMIN",
        "email_verified": True,
        "phone_number_verified": True,
        "banned": False,
        "is_anonymous": False,
        "last_login_at": datetime.now(UTC) - timedelta(hours=3),
        "login_count": 30,
    },
    {
        "email": "conservation@conservation.la",
        "password": "admin123456",
        "first_name": "Khamla",
        "last_name": "Vongsa",
        "nickname": "Seng",
        "phone_number": "+85620123456792",
        "country_code": "LAO",
        "language_pref": "lo",
        "role": "STAFF",
        "email_verified": True,
        "phone_number_verified": True,
        "banned": False,
        "is_anonymous": False,
        "last_login_at": datetime.now(UTC) - timedelta(hours=4),
        "login_count": 12,
    },
    {
        "email": "jane.smith@example.com",
        "password": "Password123!",
        "first_name": "Jane",
        "last_name": "Smith",
        "nickname": None,
        "phone_number": "+1234567891",
        "country_code": "USA",
        "language_pref": "en",
        "role": "STAFF",
        "email_verified": True,
        "phone_number_verified": True,
        "banned": False,
        "is_anonymous": False,
        "last_login_at": datetime.now(UTC) - timedelta(minutes=30),
        "login_count": 8,
    },
]


async def upload_user_image(image_file: str):
    """Upload user profile image via configured storage (local/MinIO/S3/Wasabi)."""
    try:
        image_path = f"seed/image/profile/{image_file}"

        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                file_content = f.read()

            dummy_upload_file = UploadFile(
                filename=image_file,
                file=io.BytesIO(file_content)
            )
            result = await storage_service.upload_file(dummy_upload_file, folder="users")
            if result.success and result.data:
                # Store object_name in DB (compatible with all providers)
                return result.data.get("object_name") or result.data.get("url", "")
            return f"https://example.com/profiles/{image_file}"
        return f"https://example.com/profiles/{image_file}"
    except Exception as e:
        print(f"⚠️  Error uploading image {image_file}: {str(e)}")
        return f"https://example.com/profiles/{image_file}"


def build_nickname(user_data: dict) -> str | None:
    """Build display nickname from first/last/nickname fields."""
    first = user_data.get("first_name")
    last = user_data.get("last_name")
    nick = user_data.get("nickname")

    if not first or not last:
        return None
    if nick:
        return f"{first} {nick} {last}"
    return f"{first} {last}"


def build_user_create_data(
    user_data: dict,
    hashed_password: str,
    avatar_url: str,
    nickname: str | None,
) -> dict:
    """Build the Prisma create payload from seed data."""
    return {
        "email": user_data["email"],
        "password": hashed_password,
        "first_name": user_data.get("first_name"),
        "last_name": user_data.get("last_name"),
        "nickname": nickname,
        "country_code": user_data.get("country_code"),
        "avatar_url": avatar_url,
        "language_pref": user_data.get("language_pref", "en"),
        "email_verified": user_data["email_verified"],
        "email_verified_at": datetime.now(UTC) if user_data["email_verified"] else None,
        "phone_number_verified": user_data["phone_number_verified"],
        "phone_number": user_data["phone_number"],
        "theme_pref": "dark",
        "role": user_data["role"],
        "banned": user_data["banned"],
        "ban_reason": user_data.get("ban_reason"),
        "ban_expires": user_data.get("ban_expires"),
        "is_anonymous": user_data["is_anonymous"],
        "last_login_at": user_data["last_login_at"],
        "login_count": user_data["login_count"],
        "is_active": True,
        "failed_login_attempts": 0,
        "locked_until": None,
        "last_logout_at": None,
        "deleted_at": None,
    }


async def create_single_user(user_data: dict):
    """Upload avatar, hash password, and insert one user into the database."""
    avatar_url = await upload_user_image("profile1.jpeg")
    hashed_password = hash_password(user_data["password"])
    nickname = build_nickname(user_data)
    data = build_user_create_data(user_data, hashed_password, avatar_url, nickname)
    return await prisma.user.create(data=data)


def print_summary(created_users: list) -> None:
    """Print a breakdown of the seeded users."""
    verified_emails = sum(1 for u in created_users if u.email_verified)
    verified_phones = sum(1 for u in created_users if u.phone_number_verified)
    banned = sum(1 for u in created_users if u.banned)
    admins = sum(1 for u in created_users if u.role in ['SUPER_ADMIN', 'ADMIN'])
    staff = sum(1 for u in created_users if u.role == 'STAFF')

    print("\n📊 Summary:")
    print(f"   👥 Total users: {len(created_users)}")
    print(f"   📧 Email verified: {verified_emails}")
    print(f"   📱 Phone verified: {verified_phones}")
    print(f"   🚫 Banned users: {banned}")
    print(f"   👑 Admin users: {admins}")
    print(f"   👤 Staff users: {staff}")

    missing_pw = [u.email for u in created_users if not u.password]
    print("\n🔐 Verifying user passwords...")
    if missing_pw:
        print(f"❌ {len(missing_pw)} users missing passwords:")
        for email in missing_pw:
            print(f"   - {email}")
    else:
        print(f"✅ All {len(created_users)} users have passwords")


async def seed_users_auth():
    """Seed the database with users authentication data."""
    try:
        print("👥 Starting users authentication seed data creation...")

        await connect_db()
        print("✅ Connected to database")

        print("🗑️  Clearing existing users...")
        await prisma.user.delete_many()
        print("✅ Existing users cleared")

        created_users = []
        total = len(USERS_AUTH_DATA)
        for i, user_data in enumerate(USERS_AUTH_DATA, 1):
            try:
                print(f"📝 Creating user {i}/{total}: {user_data['email']}")
                user = await create_single_user(user_data)
                created_users.append(user)
                print(f"✅ Created: {user.email}")
            except Exception as e:
                print(f"❌ Error creating {user_data['email']}: {str(e)}")
                continue

        print(f"\n🎉 Successfully created {len(created_users)} users!")
        print_summary(created_users)

        return created_users

    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        raise
    finally:
        await disconnect_db()
        print("🔌 Disconnected from database")


async def main():
    """Main function to run the seed script"""
    print("🚀 dataset Users Authentication Seed Data Script")
    print("=" * 60)

    try:
        users = await seed_users_auth()
        print("\n✅ Users authentication seed data creation completed successfully!")
        print(f"🎯 Created {len(users)} users")

    except Exception as e:
        print(f"\n❌ Users authentication seed data creation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
