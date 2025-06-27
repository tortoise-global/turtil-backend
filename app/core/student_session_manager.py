"""
Student Session Manager
Single-device session management for student mobile app
"""

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
from app.models.student import Student
from app.models.session import UserSession
from app.redis_client import CacheManager
from app.core.student_auth import student_auth
import logging

logger = logging.getLogger(__name__)


class StudentSessionManager:
    """
    Student session manager with single-device enforcement
    When student logs in from new device, all other sessions are automatically invalidated
    """

    def __init__(self):
        self.auth_manager = student_auth

    def hash_token(self, token: str) -> str:
        """Hash refresh token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def calculate_token_ttl(self, token: str) -> int:
        """Calculate remaining TTL for a JWT token based on its expiration"""
        try:
            # Decode token without verification to get expiration
            payload = jwt.decode(token, key="", options={"verify_signature": False})
            token_exp = payload.get("exp")
            
            if not token_exp:
                return 30 * 24 * 3600  # 30 days default
                
            current_time = int(time.time())
            remaining_ttl = max(0, int(token_exp - current_time))
            return max(60, remaining_ttl)  # Minimum 60 seconds for clock skew
            
        except Exception as e:
            logger.warning(f"Failed to calculate token TTL: {e}, using default")
            return 30 * 24 * 3600  # 30 days default

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

        # Device type detection (more mobile-focused)
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

    async def invalidate_all_student_sessions(
        self, 
        student_id: str, 
        db: AsyncSession = None
    ) -> bool:
        """Invalidate all existing sessions for a student (for single-device enforcement)"""
        try:
            # Get all existing session IDs for this student
            session_ids = await CacheManager.get_user_sessions(f"student_{student_id}")
            
            # Blacklist all refresh tokens and clean up sessions
            for session_id in session_ids:
                session_data = await CacheManager.get_session(f"student_session:{session_id}")
                if session_data:
                    token_hash = session_data.get("refresh_token_hash")
                    if token_hash:
                        # Calculate TTL and blacklist token
                        current_time = int(time.time())
                        session_expires_at = session_data.get("expires_at", current_time + (30 * 24 * 3600))
                        remaining_ttl = max(60, int(session_expires_at - current_time))
                        
                        await CacheManager.blacklist_refresh_token(
                            f"student_{token_hash}",
                            reason="single_device_enforcement",
                            ttl=remaining_ttl
                        )
            
            # Clear all Redis sessions for this student
            await CacheManager.invalidate_all_user_sessions(f"student_{student_id}")
            
            # Mark database sessions as inactive
            if db:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.student_id == student_id)
                    .where(UserSession.session_type == "student")
                    .values(is_active=False)
                )
                await db.commit()
            
            logger.info(f"Invalidated all sessions for student {student_id} (single-device enforcement)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate all student sessions for {student_id}: {e}")
            return False

    async def create_student_session(
        self, 
        student: Student, 
        user_agent: str = None, 
        ip_address: str = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Create new student session with single-device enforcement
        Automatically invalidates all other sessions for this student
        """
        try:
            # STEP 1: Invalidate all existing sessions (single-device enforcement)
            await self.invalidate_all_student_sessions(str(student.student_id), db)
            
            # STEP 2: Generate new session ID
            session_id_uuid = uuid.uuid4()
            session_id = str(session_id_uuid)
            
            # STEP 3: Generate tokens with session_id embedded
            access_token = self.auth_manager.create_student_access_token(student, session_id=session_id)
            refresh_token = self.auth_manager.create_student_refresh_token(student, session_id=session_id)
            
            # STEP 4: Parse device info
            device_info = self.parse_user_agent(user_agent)
            
            # STEP 5: Create timestamps
            current_time = int(time.time())
            expires_at = current_time + (30 * 24 * 3600)  # 30 days
            
            # STEP 6: Store session in database
            if db:
                db_session = UserSession(
                    session_id=session_id_uuid,
                    student_id=student.student_id,
                    session_type="student",
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
            
            # STEP 7: Store session in Redis with student prefix
            session_data = {
                "student_id": str(student.student_id),
                "refresh_token_hash": self.hash_token(refresh_token),
                "device_info": device_info,
                "created_at": current_time,
                "last_used": current_time,
                "expires_at": expires_at,
                "ip_address": ip_address
            }
            
            await CacheManager.create_session(f"student_session:{session_id}", session_data)
            await CacheManager.add_user_session(f"student_{student.student_id}", session_id)
            
            logger.info(f"Created student session {session_id} for {student.student_id} on {device_info['device']}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "session_id": session_id,
                "token_type": "bearer",
                "expires_in": self.auth_manager.get_token_expires_in(),
                "device_info": device_info,
                "single_device_mode": True
            }
            
        except Exception as e:
            logger.error(f"Failed to create student session for {student.student_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )

    async def refresh_student_session(
        self, 
        session_id: str, 
        refresh_token: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Refresh student session with mandatory token rotation"""
        try:
            # Get session from Redis with student prefix
            session_data = await CacheManager.get_session(f"student_session:{session_id}")
            if not session_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session"
                )
            
            # Validate refresh token JWT
            try:
                refresh_payload = self.auth_manager.validate_refresh_token(refresh_token)
            except HTTPException as e:
                # Re-raise auth errors
                raise e
            
            # Verify refresh token hash matches stored hash
            token_hash = self.hash_token(refresh_token)
            if token_hash != session_data.get("refresh_token_hash"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Check if token is blacklisted (with student prefix)
            if await CacheManager.is_refresh_token_blacklisted(f"student_{token_hash}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked"
                )
            
            # Check session expiry
            current_time = time.time()
            if current_time > session_data.get("expires_at", 0):
                await self.invalidate_student_session(session_id, session_data["student_id"], db)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has expired"
                )
            
            # Get student from database
            if db:
                result = await db.execute(select(Student).where(Student.student_id == session_data["student_id"]))
                student = result.scalar_one_or_none()
                if not student:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Student not found"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session required"
                )
            
            # Generate new tokens (MANDATORY ROTATION)
            new_access_token = self.auth_manager.create_student_access_token(student, session_id=session_id)
            new_refresh_token = self.auth_manager.create_student_refresh_token(student, session_id=session_id)
            new_token_hash = self.hash_token(new_refresh_token)
            
            # Blacklist old refresh token with dynamic TTL (with student prefix)
            token_ttl = self.calculate_token_ttl(refresh_token)
            await CacheManager.blacklist_refresh_token(
                f"student_{token_hash}", 
                reason="rotated", 
                ttl=token_ttl
            )
            
            # Update session data
            session_data["refresh_token_hash"] = new_token_hash
            session_data["last_used"] = current_time
            
            # Update Redis
            await CacheManager.update_session(f"student_session:{session_id}", session_data)
            
            # Update database
            if db:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.session_id == session_id)
                    .where(UserSession.session_type == "student")
                    .values(
                        refresh_token_hash=new_token_hash,
                        last_used_timestamp=current_time
                    )
                )
                await db.commit()
            
            logger.info(f"Refreshed student session {session_id} for {student.student_id}")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.auth_manager.get_token_expires_in()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to refresh student session {session_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh session"
            )

    async def get_student_current_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session information for student"""
        try:
            session_data = await CacheManager.get_session(f"student_session:{session_id}")
            if not session_data:
                return None
            
            # Check if session is expired
            current_time = time.time()
            if current_time > session_data.get("expires_at", 0):
                return None
            
            # Update last used time
            session_data["last_used"] = current_time
            await CacheManager.update_session(f"student_session:{session_id}", session_data)
            
            return {
                "student_id": session_data["student_id"],
                "session_id": session_id,
                "device_info": session_data.get("device_info", {}),
                "created_at": session_data.get("created_at"),
                "last_used": session_data.get("last_used"),
                "ip_address": session_data.get("ip_address")
            }
            
        except Exception as e:
            logger.error(f"Failed to get student session {session_id}: {e}")
            return None

    async def invalidate_student_session(
        self, 
        session_id: str, 
        student_id: str, 
        db: AsyncSession = None
    ) -> bool:
        """Invalidate a specific student session"""
        try:
            # Get session data to blacklist refresh token (with student prefix)
            session_data = await CacheManager.get_session(f"student_session:{session_id}")
            if session_data:
                token_hash = session_data.get("refresh_token_hash")
                if token_hash:
                    current_time = int(time.time())
                    session_expires_at = session_data.get("expires_at", current_time + (30 * 24 * 3600))
                    remaining_ttl = max(60, int(session_expires_at - current_time))
                    
                    await CacheManager.blacklist_refresh_token(
                        f"student_{token_hash}", 
                        reason="manual_logout",
                        ttl=remaining_ttl
                    )
            
            # Remove from Redis (with student prefix)
            await CacheManager.delete_session(f"student_session:{session_id}")
            await CacheManager.remove_user_session(f"student_{student_id}", session_id)
            
            # Mark as inactive in database
            if db:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.session_id == session_id)
                    .where(UserSession.session_type == "student")
                    .values(is_active=False)
                )
                await db.commit()
            
            logger.info(f"Invalidated student session {session_id} for {student_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate student session {session_id}: {e}")
            return False

    async def validate_student_session_token(self, session_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate student session and access token"""
        try:
            # Decode access token
            payload = self.auth_manager.validate_access_token(access_token)
            
            # Get session from Redis (with student prefix)
            session_data = await CacheManager.get_session(f"student_session:{session_id}")
            if not session_data:
                return None
            
            # Check session expiry
            current_time = time.time()
            if current_time > session_data.get("expires_at", 0):
                return None
            
            # Update last used time
            session_data["last_used"] = current_time
            await CacheManager.update_session(f"student_session:{session_id}", session_data)
            
            return {
                "student_id": session_data["student_id"],
                "session_id": session_id,
                "device_info": session_data.get("device_info", {}),
                "payload": payload
            }
            
        except Exception as e:
            logger.error(f"Failed to validate student session token: {e}")
            return None


# Global student session manager instance
student_session_manager = StudentSessionManager()