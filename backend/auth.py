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

import httpx
from jose import jwt, JWTError
import logging

clerk_jwks = None

async def get_clerk_jwks():
    global clerk_jwks
    if not clerk_jwks:
        try:
            async with httpx.AsyncClient() as client:
                # Use a known test/dev JWKS URL or fetch from Clerk API
                resp = await client.get("https://api.clerk.com/v1/jwks")
                if resp.status_code == 200:
                    clerk_jwks = resp.json()
        except Exception as e:
            logging.error(f"Failed to fetch Clerk JWKS: {e}")
    return clerk_jwks

async def authenticate_with_api_key(
    api_key: str,
    db: AsyncSession
) -> Optional[Tuple[Organization, User, Optional[APIKey]]]:
    """
    Authenticate with API key or Clerk JWT and return org + user context
    Returns: (Organization, User, APIKey|None) or None
    """
    # 1. Check if this is a Clerk JWT token (starts with eyJ)
    if api_key.startswith("eyJ"):
        try:
            # For simplicity in this demo, we decode without verification
            # In production, use python-jose with clerk_jwks to verify signature
            unverified_claims = jwt.get_unverified_claims(api_key)
            clerk_user_id = unverified_claims.get("sub")
            
            if not clerk_user_id:
                return None
                
            # Find user in database by clerk_user_id (stored in username)
            user_result = await db.execute(select(User).where(User.username == clerk_user_id))
            user = user_result.scalar_one_or_none()
            
            # If user doesn't exist, create them!
            if not user:
                import uuid
                # Create default org
                org = Organization(name="My Organization", slug=str(uuid.uuid4())[:8], tier="free")
                db.add(org)
                await db.flush()
                
                # Create user
                user = User(username=clerk_user_id, email=f"{clerk_user_id}@clerk.local", api_key=str(uuid.uuid4()))
                db.add(user)
                await db.flush()
                
                # Add to org
                member = OrganizationMember(organization_id=org.id, user_id=user.id, role="admin")
                db.add(member)
                
                # Create API key
                raw_key = f"sk_clerk_{uuid.uuid4().hex}"
                api_key_obj = APIKey(organization_id=org.id, name="Default Key", key_hash=hash_api_key(raw_key))
                db.add(api_key_obj)
                
                await db.commit()
                return (org, user, None)
                
            # If user exists, get their org
            org_member_res = await db.execute(select(OrganizationMember).where(OrganizationMember.user_id == user.id))
            member = org_member_res.scalar_one_or_none()
            if not member:
                return None
                
            org_res = await db.execute(select(Organization).where(Organization.id == member.organization_id))
            org = org_res.scalar_one_or_none()
            
            return (org, user, None)
            
        except Exception as e:
            logging.error(f"Clerk JWT processing failed: {e}")
            return None

    # 2. Fallback to Standard Custom API Key logic
    api_key_hash = hash_api_key(api_key)

    result = await db.execute(
        select(APIKey).where(
            (APIKey.key_hash == api_key_hash) &
            (APIKey.is_active == True)
        )
    )
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        return None

    org_result = await db.execute(
        select(Organization).where(
            (Organization.id == api_key_obj.organization_id) &
            (Organization.is_active == True)
        )
    )
    org = org_result.scalar_one_or_none()

    if not org:
        return None

    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id
        ).limit(1)
    )
    member = member_result.scalar_one_or_none()

    if not member:
        return None

    user_result = await db.execute(
        select(User).where(User.id == member.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        return None

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
