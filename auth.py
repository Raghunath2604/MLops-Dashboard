import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, Organization, APIKey, OrganizationMember
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


# ============================================
# UTILITY FUNCTIONS
# ============================================

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key"""
    return secrets.token_urlsafe(32)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with organization context"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token and extract org/user context"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        org_id: int = payload.get("org_id")
        if user_id is None or org_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"user_id": user_id, "org_id": org_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# ============================================
# MULTI-TENANT AUTHENTICATION FUNCTIONS
# ============================================

async def authenticate_with_api_key(
    api_key: str,
    db: AsyncSession
) -> Optional[Tuple[Organization, User, APIKey]]:
    """
    Authenticate with API key and return org + user context
    Returns: (Organization, User, APIKey) or None
    """
    api_key_hash = hash_api_key(api_key)

    # Find the API key
    result = await db.execute(
        select(APIKey).where(
            (APIKey.key_hash == api_key_hash) &
            (APIKey.is_active == True)
        )
    )
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        return None

    # Get the organization
    org_result = await db.execute(
        select(Organization).where(
            (Organization.id == api_key_obj.organization_id) &
            (Organization.is_active == True)
        )
    )
    org = org_result.scalar_one_or_none()

    if not org:
        return None

    # For now, return first member user (in real app, could have multiple users per org)
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id
        ).limit(1)
    )
    member = member_result.scalar_one_or_none()

    if not member:
        return None

    # Get the user
    user_result = await db.execute(
        select(User).where(User.id == member.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        return None

    # Update last used timestamp
    api_key_obj.last_used = datetime.utcnow()
    await db.commit()

    return (org, user, api_key_obj)


async def get_current_org_and_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(lambda: None),  # Will be injected by FastAPI
) -> Tuple[Organization, User]:
    """
    Dependency to extract organization and user from API key
    Usage: In FastAPI endpoint:
        async def my_endpoint(org_user: Tuple[Organization, User] = Depends(get_current_org_and_user)):
            org, user = org_user
    """
    # This will be implemented in app.py with proper db dependency
    pass


# ============================================
# LEGACY FUNCTIONS (for backward compatibility)
# ============================================

async def authenticate_with_credentials(
    username: str,
    api_key: str,
    db: AsyncSession
) -> Optional[User]:
    """Authenticate user with username and API key (legacy)"""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if user and user.api_key == hash_api_key(api_key):
        return user
    return None
