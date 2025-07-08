from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError
from jose import JWTError, jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.staff import Staff


# Password hashing using Argon2
password_hasher = PasswordHasher()


class AuthManager:
    """Custom authentication manager"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using Argon2"""
        try:
            return password_hasher.hash(password)
        except HashingError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error hashing password",
            )

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its Argon2 hash"""
        try:
            password_hasher.verify(hashed_password, plain_password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    @staticmethod
    def create_access_token(
        data: Dict[Any, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
        )

        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[Any, Any]) -> str:
        """Create a JWT refresh token (longer expiration)"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=7
        )  # 7 days for refresh token

        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
        )

        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )

            # Check if token has expired
            exp = payload.get("exp")
            if exp is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing expiration",
                )

            if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
                timezone.utc
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
                )

            return payload

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )

    @staticmethod
    async def authenticate_staff(
        db: AsyncSession, email: str, password: str
    ) -> Optional[Staff]:
        """Authenticate a staff with email and password"""
        # Get staff by email
        result = await db.execute(
            select(Staff).where(Staff.email == email, Staff.is_active == True)
        )
        staff = result.scalar_one_or_none()

        if not staff:
            return None

        # Verify password
        if not AuthManager.verify_password(password, staff.hashed_password):
            return None

        # Record login
        staff.record_login()
        await db.commit()

        return staff

    @staticmethod
    async def get_staff_by_token(db: AsyncSession, token: str) -> Optional[Staff]:
        """Get staff from JWT token"""
        try:
            payload = AuthManager.verify_token(token)
            staff_id: str = payload.get("sub")

            if staff_id is None:
                return None

            # Get staff by ID
            result = await db.execute(
                select(Staff).where(Staff.staff_id == staff_id, Staff.is_active == True)
            )
            staff = result.scalar_one_or_none()

            return staff

        except HTTPException:
            return None

    @staticmethod
    async def get_staff_by_email(db: AsyncSession, email: str) -> Optional[Staff]:
        """Get staff by email"""
        result = await db.execute(select(Staff).where(Staff.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_staff(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        is_verified: bool = False,
    ) -> Staff:
        """Create a new staff (hash password only when creating)"""
        # Check if staff already exists
        existing_staff = await AuthManager.get_staff_by_email(db, email)
        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff with this email already exists",
            )

        # Hash password only when creating staff
        hashed_password = AuthManager.hash_password(password)

        # Create staff
        staff = Staff(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_verified=is_verified,
        )

        db.add(staff)
        await db.commit()
        await db.refresh(staff)

        return staff


# Global auth manager instance
auth = AuthManager()
