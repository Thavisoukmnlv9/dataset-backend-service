import hashlib
import bcrypt
import jwt
from datetime import datetime, timedelta, UTC
from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with SHA256 pre-hashing.
    
    Pre-hashing with SHA256 ensures we never exceed bcrypt's 72-byte limit
    and provides consistent security regardless of password length.
    """
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    password_bytes = password_hash.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Uses SHA256 pre-hashing to match the hashing process.
    """
    password_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    password_bytes = password_hash.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 (deterministic)."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(
        UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(
        UTC) + (expires_delta or timedelta(days=settings.refresh_token_expire_days))
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


async def create_and_store_refresh_token(user_id: str, expires_delta: timedelta = None) -> str:
    """Create a refresh token and store it in the database."""
    from app.prisma import prisma

    # Calculate expiration time first
    expire_time = datetime.now(
        UTC) + (expires_delta or timedelta(days=settings.refresh_token_expire_days))

    # Generate a unique token with the exact same expiration time
    token_data = {"sub": user_id, "type": "refresh"}
    to_encode = token_data.copy()
    to_encode.update({"exp": int(expire_time.timestamp())})
    token = jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)

    # Hash the token for storage
    token_hash = hash_token(token)

    # Store in database with the exact same expiration time
    await prisma.refreshtoken.create(
        data={
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expire_time
        }
    )

    return token


async def verify_and_revoke_refresh_token(token: str) -> str:
    """Verify refresh token and return user_id if valid, then revoke it."""
    from app.prisma import prisma

    try:
        # Verify JWT token
        payload = jwt.decode(token, settings.jwt_secret,
                             algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise ValueError("Invalid token payload")

        # Hash the token to match what's stored in database
        token_hash = hash_token(token)

        # Check if token exists in database and is not expired
        db_token = await prisma.refreshtoken.find_first(
            where={
                "token_hash": token_hash,
                "expires_at": {"gt": datetime.now(UTC)},
                "is_revoked": False
            }
        )

        if not db_token:
            raise ValueError("Token not found or expired")

        # Delete the token (one-time use)
        await prisma.refreshtoken.delete(
            where={"id": db_token.id}
        )

        return user_id

    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")


async def revoke_all_user_tokens(user_id: str):
    """Revoke all refresh tokens for a user."""
    from app.prisma import prisma
    await prisma.refreshtoken.delete_many(
        where={
            "user_id": user_id
        }
    )


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret,
                             algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def validate_password_strength(password: str) -> bool:
    """Validate password strength requirements."""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True


def create_email_verification_token(data: dict, expires_in: int = 86400) -> str:
    """Create a JWT token for email verification (24 hours by default)."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(seconds=expires_in)
    to_encode.update({"exp": int(expire.timestamp()), "type": "email_verification"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def verify_email_verification_token(token: str) -> dict:
    """Verify and decode an email verification JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        
        # Check if it's an email verification token
        if payload.get("type") != "email_verification":
            raise ValueError("Invalid token type")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
