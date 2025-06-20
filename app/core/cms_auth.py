from jose import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.config import settings
from app.core.cms_otp import CMSOTPManager
from app.models.staff import Staff
from app.models.cms_permission import CMSModules, CMSRoles


class CMSAuthManager:
    """CMS Authentication Manager with JWT and Redis sessions"""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.cms_access_token_expire_minutes
        self.refresh_token_expire_days = settings.cms_refresh_token_expire_days

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Get password hash"""
        return self.pwd_context.hash(password)

    def create_access_token(self, staff: Staff) -> str:
        """Create JWT access token with staff permissions"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": str(staff.uuid),
            "email": staff.email,
            "firstName": staff.first_name,
            "lastName": staff.last_name,
            "cmsRole": staff.cms_role,
            "collegeId": staff.college_id,
            "departmentId": staff.department_id,
            "invitationStatus": staff.invitation_status,
            "mustResetPassword": staff.must_reset_password,
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, staff: Staff) -> str:
        """Create JWT refresh token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(staff.uuid),
            "email": staff.email,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_temp_token(self, staff: Staff, purpose: str = "registration") -> str:
        """Create temporary token for multi-step processes"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=30)  # 30 minutes for registration steps

        payload = {
            "sub": str(staff.uuid),
            "email": staff.email,
            "purpose": purpose,
            "exp": expire,
            "iat": now,
            "type": "temp",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    async def create_staff_session(self, staff: Staff, refresh_token: str) -> bool:
        """Create staff session in Redis with permissions"""
        try:
            # Get staff permissions based on role
            permissions = await self.get_staff_permissions(staff)

            session_data = {
                "refreshToken": refresh_token,
                "permissions": permissions,
                "role": staff.cms_role,
                "collegeId": staff.college_id,
                "departmentId": staff.department_id,
                "invitationStatus": staff.invitation_status,
                "mustResetPassword": staff.must_reset_password,
                "lastActivity": datetime.now(timezone.utc).isoformat(),
            }

            return await CMSOTPManager.store_staff_session(staff.id, session_data)

        except Exception as e:
            print(f"Error creating staff session: {e}")
            return False

    async def get_staff_permissions(self, staff: Staff) -> Dict[str, Dict[str, bool]]:
        """Get staff permissions based on role"""
        permissions = {}

        if staff.cms_role in CMSRoles.FULL_ACCESS_ROLES:
            # Principal and College Admin get full access to all modules
            for module in CMSModules.ALL_MODULES:
                permissions[module] = {"read": True, "write": True}

        elif staff.cms_role == CMSRoles.HOD:
            # HOD gets department-scoped access
            for module in CMSModules.ALL_MODULES:
                if module in CMSModules.ALWAYS_ACCESSIBLE:
                    permissions[module] = {"read": True, "write": True}
                else:
                    # Department-scoped access (configurable)
                    permissions[module] = {"read": True, "write": False}  # Default

        else:  # STAFF
            # Staff get configurable access per module
            for module in CMSModules.ALL_MODULES:
                if module in CMSModules.ALWAYS_ACCESSIBLE:
                    permissions[module] = {"read": True, "write": True}
                else:
                    permissions[module] = {"read": False, "write": False}  # Default

        return permissions

    async def validate_session(
        self, staff_id: int, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Validate staff session and return session data"""
        try:
            # Decode access token
            payload = self.decode_token(access_token)

            # Get session from Redis
            session_data = await CMSOTPManager.get_staff_session(staff_id)

            if not session_data:
                return None

            # Validate token type
            if payload.get("type") != "access":
                return None

            # Refresh session activity
            await CMSOTPManager.refresh_session_activity(staff_id)

            return session_data

        except Exception as e:
            print(f"Error validating session: {e}")
            return None

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Optional[Dict[str, str]]:
        """Refresh access token using refresh token"""
        try:
            # Decode refresh token
            payload = self.decode_token(refresh_token)

            # Validate token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            # Get staff (would need database query here)
            # For now, return structure
            return {
                "accessToken": "new_access_token",
                "refreshToken": refresh_token,  # Keep same refresh token
                "expiresIn": self.access_token_expire_minutes * 60,
            }

        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None

    async def logout_staff(self, staff_id: int) -> bool:
        """Logout staff by clearing session"""
        try:
            return await CMSOTPManager.clear_staff_session(staff_id)
        except Exception as e:
            print(f"Error logging out staff: {e}")
            return False

    async def invalidate_staff_sessions(self, staff_id: int) -> bool:
        """Invalidate all sessions for a staff (when staff is deleted/deactivated)"""
        try:
            # Clear staff session from Redis
            await CMSOTPManager.clear_staff_session(staff_id)

            # Add staff to blacklist for remaining token TTL
            blacklist_key = f"cms_blacklisted_staff:{staff_id}"
            ttl_seconds = (
                self.refresh_token_expire_days * 24 * 60 * 60
            )  # Max token lifetime

            # Store in Redis with TTL
            await CMSOTPManager.store_blacklist_entry(
                blacklist_key,
                {
                    "staff_id": staff_id,
                    "invalidated_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "staff_deleted_or_deactivated",
                },
                ttl_seconds,
            )

            print(f"Invalidated all sessions for staff {staff_id}")
            return True

        except Exception as e:
            print(f"Error invalidating staff sessions: {e}")
            return False

    async def invalidate_staff_session(
        self, staff_id: int, access_token: str
    ) -> bool:
        """Invalidate a specific staff session"""
        try:
            # Add token to blacklist
            token_blacklist_key = f"cms_blacklisted_token:{access_token}"
            ttl_seconds = self.access_token_expire_minutes * 60

            await CMSOTPManager.store_blacklist_entry(
                token_blacklist_key,
                {
                    "staff_id": staff_id,
                    "invalidated_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "staff_logout",
                },
                ttl_seconds,
            )

            # Clear session from Redis
            await CMSOTPManager.clear_staff_session(staff_id)

            return True

        except Exception as e:
            print(f"Error invalidating staff session: {e}")
            return False

    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted"""
        try:
            # Check token-specific blacklist
            token_blacklist_key = f"cms_blacklisted_token:{token}"
            token_blacklisted = await CMSOTPManager.is_blacklisted(token_blacklist_key)

            if token_blacklisted:
                return True

            # Decode token to get staff ID and check staff-level blacklist
            try:
                payload = jwt.decode(
                    token, self.secret_key, algorithms=[self.algorithm]
                )
                staff_uuid = payload.get("sub")

                if staff_uuid:
                    # Extract staff ID from token (would need database lookup in real scenario)
                    # For now, check if we can find staff blacklist by pattern
                    # This is a simplified check - in production, you'd do a proper lookup
                    pass

            except jwt.JWTError:
                # If token is invalid, treat as blacklisted
                return True

            return False

        except Exception as e:
            print(f"Error checking token blacklist: {e}")
            return False

    def generate_temporary_password(self) -> str:
        """Generate temporary password for staff invitations"""
        import secrets
        import string

        # Generate 12-character temporary password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for i in range(12))

    async def validate_permission(
        self, staff_id: int, module: str, access_type: str
    ) -> bool:
        """Validate staff permission for specific module and access type"""
        try:
            # Get session data
            session_data = await CMSOTPManager.get_staff_session(staff_id)

            if not session_data:
                return False

            # Check if module is always accessible
            if module in CMSModules.ALWAYS_ACCESSIBLE:
                return True

            # Check permissions
            permissions = session_data.get("permissions", {})
            module_perms = permissions.get(module, {})

            if access_type == "read":
                return module_perms.get("read", False)
            elif access_type == "write":
                return module_perms.get("write", False)

            return False

        except Exception as e:
            print(f"Error validating permission: {e}")
            return False

    def check_role_permission(self, staff_role: str, required_roles: list) -> bool:
        """Check if staff role has required permissions"""
        return staff_role in required_roles


# Global instance
cms_auth = CMSAuthManager()
