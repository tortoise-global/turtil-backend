from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import JWTError, jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import uuid
import time
import logging

from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.core.redis_client import redis_client
from app.models.cms.models import CMSUser

logger = logging.getLogger(__name__)


class AuthenticationManager:
    
    def __init__(self):
        self.redis = redis_client
    
    def create_access_token(self, user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> Dict[str, Any]:
        # Generate unique token ID for tracking
        token_id = str(uuid.uuid4())
        
        # Prepare JWT payload
        to_encode = user_data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        expires_in = int((expire - datetime.utcnow()).total_seconds())
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": token_id,  # JWT ID for tracking
            "sub": str(user_data.get("user_id"))
        })
        
        # Create JWT token
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Cache token in Redis for fast validation
        if self.redis.is_available():
            self.redis.cache_token(
                token_id=token_id,
                user_id=str(user_data.get("user_id")),
                expires_in=expires_in
            )
        
        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user_id": user_data.get("user_id"),
            "role": user_data.get("role"),
            "college_id": user_data.get("college_id")
        }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            # Decode JWT to get basic payload
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            user_id = payload.get("sub")
            token_id = payload.get("jti")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if user is blacklisted (immediate revocation)
            if self.redis.is_available() and self.redis.is_user_blacklisted(user_id):
                logger.warning(f"Blocked access for blacklisted user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Access revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Validate token in Redis cache if available
            if self.redis.is_available() and token_id:
                token_data = self.redis.get_token_data(token_id)
                if not token_data:
                    logger.warning(f"Token not found in cache: {token_id}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token not found",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            
            return payload
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_user_from_cache_or_db(self, user_id: str, db: Session) -> Optional[CMSUser]:
        """Get user data with cache-first approach."""
        try:
            # Try cache first if Redis is available
            if self.redis.is_available():
                cached_user = self.redis.get_cached_user(user_id)
                if cached_user:
                    logger.info(f"User {user_id} retrieved from cache")
                    # Convert cached dict back to user-like object
                    return self._dict_to_user_object(cached_user)
            
            # Cache miss or Redis unavailable - fetch from database
            logger.info(f"Cache miss for user {user_id}, fetching from database")
            user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
            
            if user and self.redis.is_available():
                # Cache the user data for next time
                user_dict = self._user_to_dict(user)
                self.redis.cache_user(user_id, user_dict)
                logger.info(f"Cached user {user_id} from database")
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def authenticate_user(self, username_or_email: str, password: str, db: Session) -> Optional[CMSUser]:
        """Authenticate user with username/email and password."""
        try:
            # Query user by username or email
            user = db.query(CMSUser).filter(
                (CMSUser.username == username_or_email) | 
                (CMSUser.email == username_or_email)
            ).first()
            
            if not user:
                logger.warning(f"User not found: {username_or_email}")
                return None
            
            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning(f"Invalid password for user: {username_or_email}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Inactive user attempted login: {username_or_email}")
                return None
            
            # Check Redis blacklist
            if self.redis.is_available() and self.redis.is_user_blacklisted(str(user.id)):
                logger.warning(f"Blacklisted user attempted login: {username_or_email}")
                return None
            
            # Update last login
            user.last_login = int(time.time())
            db.commit()
            
            # Cache user data
            if self.redis.is_available():
                user_dict = self._user_to_dict(user)
                self.redis.cache_user(str(user.id), user_dict)
            
            logger.info(f"User authenticated successfully: {username_or_email}")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error for {username_or_email}: {e}")
            return None
    
    def revoke_user_access(self, user_id: str, reason: str = "admin_revoked") -> bool:
        """Immediately revoke user access by blacklisting."""
        try:
            success = True
            
            # Add to blacklist for immediate effect
            if self.redis.is_available():
                blacklist_success = self.redis.blacklist_user(user_id, reason)
                # Invalidate all user tokens
                tokens_success = self.redis.invalidate_all_user_tokens(user_id)
                success = blacklist_success and tokens_success
            else:
                logger.warning("Redis unavailable - cannot provide immediate revocation")
                success = False
            
            logger.info(f"User access revoked: {user_id}, reason: {reason}")
            return success
            
        except Exception as e:
            logger.error(f"Error revoking access for user {user_id}: {e}")
            return False
    
    def restore_user_access(self, user_id: str) -> bool:
        """Restore user access by removing from blacklist."""
        try:
            if self.redis.is_available():
                success = self.redis.remove_from_blacklist(user_id)
                logger.info(f"User access restored: {user_id}")
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Error restoring access for user {user_id}: {e}")
            return False
    
    def invalidate_token(self, token: str) -> bool:
        """Invalidate specific token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            token_id = payload.get("jti")
            
            if token_id and self.redis.is_available():
                return self.redis.invalidate_token(token_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Error invalidating token: {e}")
            return False
    
    def get_authentication_status(self, user_id: str) -> Dict[str, Any]:
        """Get detailed authentication status for user."""
        try:
            status_info = {
                "user_id": user_id,
                "is_blacklisted": False,
                "cache_available": self.redis.is_available(),
                "cached_user": False
            }
            
            if self.redis.is_available():
                # Check blacklist status
                status_info["is_blacklisted"] = self.redis.is_user_blacklisted(user_id)
                
                # Check if user is cached
                cached_user = self.redis.get_cached_user(user_id)
                status_info["cached_user"] = cached_user is not None
                
                if cached_user:
                    status_info["cache_data"] = {
                        "username": cached_user.get("username"),
                        "role": cached_user.get("role"),
                        "is_active": cached_user.get("is_active")
                    }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting auth status for user {user_id}: {e}")
            return {"error": str(e)}
    
    def _user_to_dict(self, user: CMSUser) -> Dict[str, Any]:
        """Convert SQLAlchemy user object to dictionary for caching."""
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "college_id": str(user.college_id),
            "department_id": str(user.department_id) if user.department_id else None,
            "branch_id": str(user.branch_id) if user.branch_id else None,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    
    def _dict_to_user_object(self, user_dict: Dict[str, Any]) -> CMSUser:
        """Convert cached dictionary back to user-like object."""
        # Create a mock user object with the cached data
        user = CMSUser()
        user.id = user_dict["id"]
        user.username = user_dict["username"]
        user.email = user_dict["email"]
        user.full_name = user_dict["full_name"]
        user.role = user_dict["role"]
        user.college_id = user_dict["college_id"]
        user.department_id = user_dict.get("department_id")
        user.branch_id = user_dict.get("branch_id")
        user.is_active = user_dict["is_active"]
        user.email_verified = user_dict["email_verified"]
        user.created_at = user_dict["created_at"]
        user.last_login = user_dict.get("last_login")
        return user


# Global authentication manager instance
auth_manager = AuthenticationManager()