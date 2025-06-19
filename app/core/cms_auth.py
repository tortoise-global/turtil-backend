from jose import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.config import settings
from app.core.cms_otp import CMSOTPManager
from app.models.user import User
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
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token with user permissions"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user.uuid),
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "cmsRole": user.cms_role,
            "collegeId": user.college_id,
            "departmentId": user.department_id,
            "invitationStatus": user.invitation_status,
            "mustResetPassword": user.must_reset_password,
            "exp": expire,
            "iat": now,
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": str(user.uuid),
            "email": user.email,
            "exp": expire,
            "iat": now,
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_temp_token(self, user: User, purpose: str = "registration") -> str:
        """Create temporary token for multi-step processes"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=30)  # 30 minutes for registration steps
        
        payload = {
            "sub": str(user.uuid),
            "email": user.email,
            "purpose": purpose,
            "exp": expire,
            "iat": now,
            "type": "temp"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def create_user_session(self, user: User, refresh_token: str) -> bool:
        """Create user session in Redis with permissions"""
        try:
            # Get user permissions based on role
            permissions = await self.get_user_permissions(user)
            
            session_data = {
                "refreshToken": refresh_token,
                "permissions": permissions,
                "role": user.cms_role,
                "collegeId": user.college_id,
                "departmentId": user.department_id,
                "invitationStatus": user.invitation_status,
                "mustResetPassword": user.must_reset_password,
                "lastActivity": datetime.now(timezone.utc).isoformat()
            }
            
            return await CMSOTPManager.store_user_session(user.id, session_data)
            
        except Exception as e:
            print(f"Error creating user session: {e}")
            return False
    
    async def get_user_permissions(self, user: User) -> Dict[str, Dict[str, bool]]:
        """Get user permissions based on role"""
        permissions = {}
        
        if user.cms_role in CMSRoles.FULL_ACCESS_ROLES:
            # Principal and College Admin get full access to all modules
            for module in CMSModules.ALL_MODULES:
                permissions[module] = {"read": True, "write": True}
        
        elif user.cms_role == CMSRoles.HOD:
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
    
    async def validate_session(self, cms_user_id: int, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate user session and return session data"""
        try:
            # Decode access token
            payload = self.decode_token(access_token)
            
            # Get session from Redis
            session_data = await CMSOTPManager.get_user_session(cms_user_id)
            
            if not session_data:
                return None
            
            # Validate token type
            if payload.get("type") != "access":
                return None
            
            # Refresh session activity
            await CMSOTPManager.refresh_session_activity(cms_user_id)
            
            return session_data
            
        except Exception as e:
            print(f"Error validating session: {e}")
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh access token using refresh token"""
        try:
            # Decode refresh token
            payload = self.decode_token(refresh_token)
            
            # Validate token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Get user (would need database query here)
            # For now, return structure
            return {
                "accessToken": "new_access_token",
                "refreshToken": refresh_token,  # Keep same refresh token
                "expiresIn": self.access_token_expire_minutes * 60
            }
            
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    
    async def logout_user(self, cms_user_id: int) -> bool:
        """Logout user by clearing session"""
        try:
            return await CMSOTPManager.clear_user_session(cms_user_id)
        except Exception as e:
            print(f"Error logging out user: {e}")
            return False
    
    def generate_temporary_password(self) -> str:
        """Generate temporary password for user invitations"""
        import secrets
        import string
        
        # Generate 12-character temporary password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for i in range(12))
    
    async def validate_permission(self, cms_user_id: int, module: str, access_type: str) -> bool:
        """Validate user permission for specific module and access type"""
        try:
            # Get session data
            session_data = await CMSOTPManager.get_user_session(cms_user_id)
            
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
    
    def check_role_permission(self, user_role: str, required_roles: list) -> bool:
        """Check if user role has required permissions"""
        return user_role in required_roles


# Global instance
cms_auth = CMSAuthManager()