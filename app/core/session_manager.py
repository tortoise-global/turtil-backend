import hashlib
import json
import time
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete as sql_delete
from fastapi import HTTPException, status
from jose import jwt
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.models.staff import Staff
from app.models.session import UserSession
from app.redis_client import CacheManager
from app.core.cms_auth import CMSAuthManager
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Enhanced session manager with multi-device support and Redis integration"""

    def __init__(self):
        self.auth_manager = CMSAuthManager()

    def hash_token(self, token: str) -> str:
        """Hash refresh token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def calculate_token_ttl(self, token: str) -> int:
        """Calculate remaining TTL for a JWT token based on its expiration"""
        try:
            # Decode token without verification to get expiration (we just need the timestamp)
            payload = jwt.decode(token, key="", options={"verify_signature": False})
            token_exp = payload.get("exp")
            
            if not token_exp:
                # If no expiration in token, use default TTL
                return 30 * 24 * 3600  # 30 days default
                
            current_time = int(time.time())
            remaining_ttl = max(0, int(token_exp - current_time))
            
            # Ensure we have at least 60 seconds TTL to account for clock skew
            return max(60, remaining_ttl)
            
        except Exception as e:
            logger.warning(f"Failed to calculate token TTL: {e}, using default")
            # If we can't decode the token, use default TTL for safety
            return 30 * 24 * 3600  # 30 days default
    
    def decode_access_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate access token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

    def parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """Parse user agent string to extract device info"""
        if not user_agent:
            return {"browser": "Unknown", "os": "Unknown", "device": "Unknown"}

        user_agent = user_agent.lower()
        
        # Browser detection
        browser = "Unknown"
        if "chrome" in user_agent and "edg" not in user_agent:
            browser = "Chrome"
        elif "firefox" in user_agent:
            browser = "Firefox"
        elif "safari" in user_agent and "chrome" not in user_agent:
            browser = "Safari"
        elif "edg" in user_agent:
            browser = "Edge"
        elif "opera" in user_agent:
            browser = "Opera"

        # OS detection
        os_name = "Unknown"
        if "windows" in user_agent:
            os_name = "Windows"
        elif "macintosh" in user_agent or "mac os" in user_agent:
            os_name = "macOS"
        elif "linux" in user_agent:
            os_name = "Linux"
        elif "android" in user_agent:
            os_name = "Android"
        elif "iphone" in user_agent or "ipad" in user_agent:
            os_name = "iOS"

        # Device type detection
        device = "Desktop"
        if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
            device = "Mobile"
        elif "tablet" in user_agent or "ipad" in user_agent:
            device = "Tablet"

        return {
            "browser": browser,
            "os": os_name,
            "device": device
        }

    async def create_session(
        self, 
        staff: Staff, 
        user_agent: str = None, 
        ip_address: str = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Create new session with device tracking"""
        try:
            # Generate session ID first
            session_id_uuid = uuid.uuid4()
            session_id = str(session_id_uuid)
            
            # Generate tokens with session_id embedded
            access_token = self.auth_manager.create_access_token(staff, session_id=session_id)
            refresh_token = self.auth_manager.create_refresh_token(staff, session_id=session_id)
            
            # Parse device info
            device_info = self.parse_user_agent(user_agent)
            
            # Create timestamps
            current_time = int(time.time())
            expires_at = current_time + (30 * 24 * 3600)  # 30 days
            
            # Store session in database
            if db:
                db_session = UserSession(
                    session_id=session_id_uuid,
                    staff_id=staff.staff_id,
                    browser=device_info["browser"],
                    os=device_info["os"],
                    device=device_info["device"],
                    user_agent=user_agent,
                    refresh_token_hash=self.hash_token(refresh_token),
                    created_at_timestamp=current_time,
                    last_used_timestamp=current_time,
                    expires_at_timestamp=expires_at,
                    is_active=True,
                    ip_address=ip_address
                )
                db.add(db_session)
                await db.commit()
                await db.refresh(db_session)
            
            # Store session in Redis
            session_data = {
                "staff_id": str(staff.staff_id),  # Convert UUID to string for JSON serialization
                "refresh_token_hash": self.hash_token(refresh_token),
                "device_info": device_info,
                "created_at": current_time,
                "last_used": current_time,
                "expires_at": expires_at,
                "ip_address": ip_address
            }
            
            await CacheManager.create_session(session_id, session_data)
            await CacheManager.add_user_session(str(staff.staff_id), session_id)
            
            logger.info(f"Created session {session_id} for staff {staff.staff_id} on {device_info['device']}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "session_id": session_id,
                "token_type": "bearer",
                "expires_in": settings.cms_access_token_expire_minutes * 60,
                "device_info": device_info
            }
            
        except Exception as e:
            logger.error(f"Failed to create session for staff {staff.staff_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )

    async def refresh_session(
        self, 
        session_id: str, 
        refresh_token: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Refresh session with mandatory token rotation"""
        try:
            # Get session from Redis
            session_data = await CacheManager.get_session(session_id)
            if not session_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session"
                )
            
            # Decode and validate refresh token JWT
            try:
                refresh_payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
                if refresh_payload.get("type") != "refresh":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token type"
                    )
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has expired"
                )
            except jwt.JWTError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Verify refresh token hash matches stored hash
            token_hash = self.hash_token(refresh_token)
            if token_hash != session_data.get("refresh_token_hash"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Check if token is blacklisted
            if await CacheManager.is_refresh_token_blacklisted(token_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked"
                )
            
            # Check session expiry
            current_time = time.time()
            if current_time > session_data.get("expires_at", 0):
                await self.invalidate_session(session_id, session_data["staff_id"], db)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has expired"
                )
            
            # Get staff from database
            if db:
                result = await db.execute(select(Staff).where(Staff.staff_id == session_data["staff_id"]))
                staff = result.scalar_one_or_none()
                if not staff:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session required"
                )
            
            # Generate new tokens (MANDATORY ROTATION)
            new_access_token = self.auth_manager.create_access_token(staff, session_id=session_id)
            new_refresh_token = self.auth_manager.create_refresh_token(staff, session_id=session_id)
            new_token_hash = self.hash_token(new_refresh_token)
            
            # Blacklist old refresh token with dynamic TTL
            token_ttl = self.calculate_token_ttl(refresh_token)
            await CacheManager.blacklist_refresh_token(
                token_hash, 
                reason="rotated", 
                ttl=token_ttl
            )
            
            # Update session data
            session_data["refresh_token_hash"] = new_token_hash
            session_data["last_used"] = current_time
            
            # Update Redis
            await CacheManager.update_session(session_id, session_data)
            
            # Update database
            if db:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.session_id == session_id)
                    .values(
                        refresh_token_hash=new_token_hash,
                        last_used_timestamp=current_time
                    )
                )
                await db.commit()
            
            logger.info(f"Refreshed session {session_id} for staff {staff.staff_id}")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": settings.cms_access_token_expire_minutes * 60
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to refresh session {session_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh session"
            )

    async def get_user_sessions(self, staff_id: int, db: AsyncSession = None) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        try:
            sessions = []
            
            # Get session IDs from Redis
            session_ids = await CacheManager.get_user_sessions(staff_id)
            
            for session_id in session_ids:
                # Get session data from Redis
                session_data = await CacheManager.get_session(session_id)
                if session_data:
                    # Check if session is expired
                    current_time = time.time()
                    if current_time > session_data.get("expires_at", 0):
                        # Clean up expired session
                        await self.invalidate_session(session_id, staff_id, db)
                        continue
                    
                    # Format session for response
                    device_info = session_data.get("device_info", {})
                    sessions.append({
                        "session_id": session_id,
                        "device": device_info.get("device", "Unknown"),
                        "browser": device_info.get("browser", "Unknown"),
                        "os": device_info.get("os", "Unknown"),
                        "created_at": session_data.get("created_at"),
                        "last_used": session_data.get("last_used"),
                        "ip_address": session_data.get("ip_address")
                    })
                else:
                    # Clean up stale session ID
                    await CacheManager.remove_user_session(staff_id, session_id)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for staff {staff_id}: {e}")
            return []

    async def invalidate_session(
        self, 
        session_id: str, 
        staff_id: int, 
        db: AsyncSession = None
    ) -> bool:
        """Invalidate a specific session"""
        try:
            # Get session data to blacklist refresh token
            session_data = await CacheManager.get_session(session_id)
            if session_data:
                token_hash = session_data.get("refresh_token_hash")
                if token_hash:
                    # Calculate TTL based on session expiry
                    current_time = int(time.time())
                    session_expires_at = session_data.get("expires_at", current_time + (30 * 24 * 3600))
                    remaining_ttl = max(60, int(session_expires_at - current_time))
                    
                    await CacheManager.blacklist_refresh_token(
                        token_hash, 
                        reason="manual_logout",
                        ttl=remaining_ttl
                    )
            
            # Remove from Redis
            await CacheManager.delete_session(session_id)
            await CacheManager.remove_user_session(staff_id, session_id)
            
            # Mark as inactive in database
            if db:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.session_id == session_id)
                    .values(is_active=False)
                )
                await db.commit()
            
            logger.info(f"Invalidated session {session_id} for staff {staff_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False

    async def invalidate_all_user_sessions(
        self, 
        staff_id: int, 
        except_session_id: str = None,
        db: AsyncSession = None
    ) -> bool:
        """Invalidate all sessions for a user (password reset or logout all)"""
        try:
            # Get all session IDs
            session_ids = await CacheManager.get_user_sessions(staff_id)
            
            # Blacklist all refresh tokens
            for session_id in session_ids:
                if except_session_id and session_id == except_session_id:
                    continue
                    
                session_data = await CacheManager.get_session(session_id)
                if session_data:
                    token_hash = session_data.get("refresh_token_hash")
                    if token_hash:
                        # Calculate TTL based on session expiry
                        current_time = int(time.time())
                        session_expires_at = session_data.get("expires_at", current_time + (30 * 24 * 3600))
                        remaining_ttl = max(60, int(session_expires_at - current_time))
                        
                        await CacheManager.blacklist_refresh_token(
                            token_hash,
                            reason="logout_all",
                            ttl=remaining_ttl
                        )
            
            # Clear Redis sessions
            await CacheManager.invalidate_all_user_sessions(staff_id)
            
            # Mark database sessions as inactive
            if db:
                query = update(UserSession).where(UserSession.staff_id == staff_id)
                if except_session_id:
                    query = query.where(UserSession.session_id != except_session_id)
                await db.execute(query.values(is_active=False))
                await db.commit()
            
            logger.info(f"Invalidated all sessions for staff {staff_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate all sessions for staff {staff_id}: {e}")
            return False

    async def validate_session_token(self, session_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate session and access token"""
        try:
            # Decode access token
            payload = self.auth_manager.decode_token(access_token)
            
            # Get session from Redis
            session_data = await CacheManager.get_session(session_id)
            if not session_data:
                return None
            
            # Validate token type
            if payload.get("type") != "access":
                return None
            
            # Check session expiry
            current_time = time.time()
            if current_time > session_data.get("expires_at", 0):
                return None
            
            # Update last used time
            session_data["last_used"] = current_time
            await CacheManager.update_session(session_id, session_data)
            
            return {
                "staff_id": session_data["staff_id"],
                "session_id": session_id,
                "device_info": session_data.get("device_info", {}),
                "created_at": session_data.get("created_at"),
                "last_used": session_data.get("last_used"),
                "ip_address": session_data.get("ip_address")
            }
            
        except Exception as e:
            logger.error(f"Failed to validate session token: {e}")
            return None

    async def cleanup_expired_sessions(self, db: AsyncSession = None):
        """Background task to cleanup expired sessions"""
        try:
            current_time = time.time()
            
            # Get all session keys from Redis
            session_keys = await CacheManager.redis_client.scan_keys("session:*")
            
            expired_count = 0
            for key in session_keys:
                session_data = await CacheManager.get_session(key.split(":")[1])
                if session_data and session_data.get("expires_at", 0) < current_time:
                    session_id = key.split(":")[1]
                    staff_id = session_data.get("staff_id")
                    
                    # Remove expired session
                    await CacheManager.delete_session(session_id)
                    if staff_id:
                        await CacheManager.remove_user_session(staff_id, session_id)
                    
                    expired_count += 1
            
            # Cleanup database sessions
            if db:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.expires_at_timestamp < current_time)
                    .values(is_active=False)
                )
                await db.commit()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")


# Global session manager instance
session_manager = SessionManager()