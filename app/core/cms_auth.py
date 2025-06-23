from jose import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.config import settings
from app.core.cms_otp import CMSOTPManager
from app.models.staff import Staff
from app.models.permission import CMSModules, CMSRoles


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

    def create_access_token(self, staff: Staff, session_id: str = None) -> str:
        """Create JWT access token with staff permissions and registration state"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        # Determine if user requires password reset
        requires_password_reset = (
            staff.must_reset_password or 
            staff.temporary_password or
            (staff.invitation_status == "pending" and staff.hashed_password)
        )
        
        # Determine granular registration step completion
        personal_details_completed = bool(staff.full_name and staff.full_name.strip())
        college_details_completed = staff.college_id is not None
        address_details_completed = college_details_completed  # Address is part of college creation
        
        # Overall registration completion check
        requires_details = (
            not personal_details_completed or
            not college_details_completed or
            not address_details_completed or
            staff.invitation_status == "pending"
        )

        payload = {
            "sub": str(staff.uuid),
            "email": staff.email,
            "fullName": staff.full_name,
            "cmsRole": staff.cms_role,
            "collegeId": staff.college_id,
            "departmentId": staff.department_id,
            "invitationStatus": staff.invitation_status,
            "isHod": staff.is_hod,
            "requiresPasswordReset": requires_password_reset,
            "requiresDetails": requires_details,
            # Granular registration step flags
            "personalDetailsCompleted": personal_details_completed,
            "collegeDetailsCompleted": college_details_completed,
            "addressDetailsCompleted": address_details_completed,
            "exp": expire,
            "iat": now,
            "type": "access",
        }
        
        # Add session_id if provided (for multi-device sessions)
        if session_id:
            payload["session_id"] = session_id

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    async def refresh_user_tokens(self, staff: Staff) -> dict:
        """
        Generate new JWT tokens for staff and invalidate old session
        Used after registration step completion to update JWT flags
        """
        # Generate new tokens with updated staff state
        access_token = self.create_access_token(staff)
        refresh_token = self.create_refresh_token(staff)
        
        # Invalidate old sessions (user will use new tokens)
        await self.invalidate_staff_sessions(staff.id)
        
        # Create new session
        await self.create_staff_session(staff, access_token)
        
        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "bearer",
            "expiresIn": self.access_token_expire_minutes * 60,
        }

    def create_refresh_token(self, staff: Staff, session_id: str = None) -> str:
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
        
        # Add session_id if provided (for multi-device sessions)
        if session_id:
            payload["session_id"] = session_id

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_temp_token(self, staff: Staff, purpose: str = "registration") -> str:
        """Create temporary token for multi-step processes"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)  # Normal JWT expiry

        payload = {
            "sub": str(staff.uuid),
            "email": staff.email,
            "staffId": staff.id,
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

            # Determine flow control flags (same logic as JWT)
            requires_password_reset = (
                staff.must_reset_password or 
                staff.temporary_password or
                (staff.invitation_status == "pending" and staff.hashed_password)
            )
            
            requires_details = (
                not staff.college_id or 
                (staff.cms_role == "principal" and staff.invitation_status == "pending")
            )

            session_data = {
                "refreshToken": refresh_token,
                "permissions": permissions,
                "role": staff.cms_role,
                "collegeId": staff.college_id,
                "departmentId": staff.department_id,
                "invitationStatus": staff.invitation_status,
                "requiresPasswordReset": requires_password_reset,
                "requiresDetails": requires_details,
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

    async def validate_temp_token(self, token: str, required_purpose: str = None) -> Optional[Dict[str, Any]]:
        """Validate temporary token and return payload"""
        try:
            # Decode temp token
            payload = self.decode_token(token)

            # Validate token type
            if payload.get("type") != "temp":
                return None

            # Validate purpose if specified
            if required_purpose and payload.get("purpose") != required_purpose:
                return None

            # For registration temp tokens, we trust they were created after OTP verification
            # No need to re-check OTP status since the token itself proves OTP was verified
            # when it was created. OTP verification is handled at the endpoint level if needed.

            return payload

        except Exception as e:
            print(f"Error validating temp token: {e}")
            return None

    async def validate_temp_token_with_otp(self, token: str, email: str) -> bool:
        """Validate temp token and ensure OTP is still verified for the email"""
        try:
            payload = await self.validate_temp_token(token, "registration")
            if not payload:
                return False

            # Check if token email matches provided email
            if payload.get("email") != email:
                return False

            # Check if OTP is still verified
            return await CMSOTPManager.is_otp_verified(email)

        except Exception as e:
            print(f"Error validating temp token with OTP: {e}")
            return False

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
