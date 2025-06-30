"""
Simplified Session API
Multi-device authentication, session tracking, and token management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
from jose.exceptions import JWTError

from app.database import get_db
from app.models.staff import Staff
from app.core.session_manager import session_manager
from app.schemas.session_schemas import (
    SigninRequest,
    RefreshTokenRequest,
    SigninResponse,
    RefreshTokenResponse,
    SessionListResponse,
    CurrentSessionResponse,
    LogoutResponse,
    SessionInfo,
    DeviceInfo
)
import logging

router = APIRouter(prefix="/auth/session", tags=["CMS Authentication - Session Management"])
logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host if request.client else "unknown"


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Dependency to get current session information from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    try:
        # Decode JWT token to get session information
        payload = session_manager.decode_access_token(credentials.credentials)
        staff_id = payload.get("sub")
        session_id = payload.get("session_id")  # Session ID embedded in JWT
        
        if not staff_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get staff information
        result = await db.execute(select(Staff).where(Staff.staff_id == staff_id))
        staff = result.scalar_one_or_none()
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # If session_id is present in token, validate full session
        if session_id:
            session_info = await session_manager.validate_session_token(session_id, credentials.credentials)
            if not session_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session"
                )
            
            return {
                "staff": staff,
                "session_id": session_id,
                "session_info": session_info
            }
        else:
            # No session_id in token - invalid token format
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format. Please sign in again."
            )
            
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


@router.post("/signin", response_model=SigninResponse)
async def signin(
    request: SigninRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sign in with email and password - Complete Authentication Flow
    Creates a new session with device tracking and returns complete token information
    
    **Authentication Flow:**
    1. Use this endpoint to get both `accessToken` and `refreshToken`
    2. Use the `accessToken` in Authorization header for subsequent requests
    3. Use `/refresh` endpoint when access token expires
    
    **Response includes:**
    - `accessToken`: For immediate API access (15 minutes)
    - `refreshToken`: For getting new access tokens (30 days)
    - `deviceInfo`: Browser, OS, and device type information
    - `staff`: Complete user profile information
    
    **Security Features:**
    - Multi-device session tracking
    - Mandatory token rotation on refresh
    - Device fingerprinting for security monitoring
    """
    try:
        email = request.email.lower().strip()
        
        # Find staff by email
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        from app.core.cms_auth import cms_auth
        if not cms_auth.verify_password(request.password, staff.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active and verified
        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        if not staff.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please complete registration first."
            )
        
        # Get device information
        user_agent = http_request.headers.get("User-Agent", "")
        ip_address = get_client_ip(http_request)
        
        # Create multi-device session
        session_data = await session_manager.create_session(
            staff=staff,
            user_agent=user_agent,
            ip_address=ip_address,
            db=db
        )
        
        # Update login tracking
        staff.record_login()
        await db.commit()
        
        
        logger.info(f"Signin successful for {email} from {ip_address}")
        
        
        # Send login notification email (non-blocking)
        try:
            from app.core.aws import EmailService
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            await EmailService.send_login_notification_email(
                email=email,
                full_name=staff.full_name,
                device_info=session_data["device_info"],
                ip_address=ip_address,
                timestamp=timestamp
            )
        except Exception as e:
            # Don't fail login if notification email fails
            logger.warning(f"Failed to send login notification email to {email}: {e}")
        
        # Return response with both tokens in JSON payload
        return {
            "access_token": session_data["access_token"],
            "refresh_token": session_data["refresh_token"],
            "token_type": "bearer",
            "expires_in": 15 * 60,  # 15 minutes
            "device_info": session_data["device_info"],
            "staff": staff.to_dict(),
            "message": "Sign in successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Signin", {"user_email": request.email, "ip_address": get_client_ip(http_request)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_tokens(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    Mandatory token rotation for security
    
    **Request Body:**
    - `refreshToken`: The refresh token to use for getting new tokens
    
    **Note:** Session ID is automatically extracted from the refresh token JWT payload
    """
    try:
        # Check if refresh token is present in request
        refresh_token = request.refresh_token
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token found. Please sign in again."
            )
        
        # Extract session_id from refresh token JWT payload
        try:
            # Decode without verification to extract session_id (we'll verify in refresh_session)
            payload = jwt.decode(refresh_token, key="", options={"verify_signature": False})
            session_id = payload.get("session_id")
            
            # Require session_id in token
            if not session_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token format. Please sign in again."
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token format"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token processing error: {str(e)}"
            )
        
        # Refresh session with mandatory token rotation
        token_data = await session_manager.refresh_session(
            session_id=session_id,
            refresh_token=refresh_token,
            db=db
        )
        
        logger.info(f"Token refreshed for session {session_id}")
        
        
        return RefreshTokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Token refresh", {"refresh_token_provided": bool(request.refresh_token)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/list", response_model=SessionListResponse)
async def list_sessions(
    current_session: dict = Depends(get_current_session),
    db: AsyncSession = Depends(get_db)
):
    """
    List all active sessions for the current user
    
    **Authentication Required:**
    - **Authorization**: Bearer token from signin
    
    **How to test in Swagger:**
    1. First use `/auth/session/signin` to get access token
    2. Click 'Authorize' button and enter: `Bearer YOUR_ACCESS_TOKEN`
    
    **Response includes:**
    - List of all your active sessions across devices
    - Device information (browser, OS, etc.)
    - Session creation time and last activity
    - Which session is currently being used
    """
    try:
        staff = current_session["staff"]
        current_session_id = current_session["session_id"]
        
        # Get all user sessions
        sessions_data = await session_manager.get_user_sessions(staff.staff_id, db)
        
        # Format sessions for response
        sessions = []
        for session_data in sessions_data:
            sessions.append(SessionInfo(
                session_id=session_data["session_id"],
                device=session_data["device"],
                browser=session_data["browser"],
                os=session_data["os"],
                created_at=int(session_data["created_at"]),
                last_used=int(session_data["last_used"]),
                ip_address=session_data.get("ip_address"),
                is_current=(session_data["session_id"] == current_session_id)
            ))
        
        return SessionListResponse(
            sessions=sessions,
            total_count=len(sessions)
        )
        
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "List sessions", {"staff_id": str(current_session['staff'].staff_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/current", response_model=CurrentSessionResponse)
async def get_current_session_info(
    current_session: dict = Depends(get_current_session)
):
    """
    Get current session information
    """
    try:
        session_info = current_session["session_info"]
        
        return CurrentSessionResponse(
            session_id=current_session["session_id"],
            device_info=DeviceInfo(**session_info["device_info"]),
            created_at=int(session_info.get("created_at", 0)),
            last_used=int(session_info.get("last_used", 0)),
            ip_address=session_info.get("ip_address")
        )
        
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get current session", {"session_id": current_session.get("session_id", "unknown")}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/signout", response_model=LogoutResponse)
async def signout(
    current_session: dict = Depends(get_current_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Sign out from current session
    
    **Authentication Required:**
    - **Authorization**: Bearer token from signin
    
    **Note:** Session ID is automatically extracted from the access token
    """
    try:
        staff = current_session["staff"]
        session_id = current_session["session_id"]
        
        # Invalidate current session
        success = await session_manager.invalidate_session(session_id, staff.staff_id, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sign out"
            )
        
        logger.info(f"User {staff.email} signed out from session {session_id}")
        
        
        return LogoutResponse(
            success=True,
            message="Successfully signed out",
            sessions_invalidated=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Signout", {"staff_id": str(current_session['staff'].staff_id), "session_id": current_session.get("session_id")}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/all", response_model=LogoutResponse)
async def signout_all_sessions(
    current_session: dict = Depends(get_current_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Sign out from all sessions except current
    """
    try:
        staff = current_session["staff"]
        current_session_id = current_session["session_id"]
        
        # Get session count before invalidation
        user_sessions = await session_manager.get_user_sessions(staff.staff_id, db)
        other_sessions_count = len([s for s in user_sessions if s["session_id"] != current_session_id])
        
        # Invalidate all sessions except current
        success = await session_manager.invalidate_all_user_sessions(
            staff.staff_id, 
            except_session_id=current_session_id,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sign out all sessions"
            )
        
        logger.info(f"User {staff.email} signed out {other_sessions_count} other sessions")
        
        return LogoutResponse(
            success=True,
            message=f"Successfully signed out from {other_sessions_count} other devices",
            sessions_invalidated=other_sessions_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Signout all sessions", {"staff_id": str(current_session['staff'].staff_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{sessionId}", response_model=LogoutResponse)
async def signout_specific_session(
    sessionId: str,
    current_session: dict = Depends(get_current_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Sign out from a specific session (logout another device)
    """
    try:
        staff = current_session["staff"]
        
        # Validate that the session belongs to the current user
        user_sessions = await session_manager.get_user_sessions(staff.staff_id, db)
        valid_session_ids = [s["session_id"] for s in user_sessions]
        
        if sessionId not in valid_session_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Prevent users from signing out their current session via this endpoint
        if sessionId == current_session["session_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use /signout endpoint to sign out current session"
            )
        
        # Invalidate the specific session
        success = await session_manager.invalidate_session(sessionId, staff.staff_id, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sign out session"
            )
        
        logger.info(f"User {staff.email} signed out session {sessionId}")
        
        return LogoutResponse(
            success=True,
            message="Successfully signed out from device",
            sessions_invalidated=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Signout specific session", {"staff_id": str(current_session['staff'].staff_id), "target_session_id": sessionId}, status.HTTP_500_INTERNAL_SERVER_ERROR)