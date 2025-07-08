from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas.email_schemas import (
    SendEmailRequest,
    EmailResponse,
    VerifyEmailOTPRequest,
    VerifyEmailOTPResponse,
)
from app.models.email_otp import CmsEmailOTP
from app.core.aws import get_ses_client
import random
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/send-email", response_model=EmailResponse)
async def send_email_otp(request: SendEmailRequest, db: AsyncSession = Depends(get_db)):
    """
    Send OTP to email address for verification
    This is your exact existing code integrated into the FastAPI structure
    """
    try:
        # Generate a 6-digit OTP
        otp = random.randint(100000, 999999)

        logger.info(f"Generated OTP: {otp} for email: {request.email}")

        # Calculate expiration time (5 minutes from now) in seconds (Unix timestamp)
        current_time = datetime.now(timezone.utc)
        expiry_time = int((current_time + timedelta(minutes=5)).timestamp())

        # Check if OTP record already exists for this email
        stmt = select(CmsEmailOTP).where(CmsEmailOTP.email == request.email)
        result = await db.execute(stmt)
        existing_otp = result.scalar_one_or_none()

        if existing_otp:
            # Update existing record
            existing_otp.otp = otp
            existing_otp.expiry = int(expiry_time)
        else:
            # Create new OTP record
            otp_record = CmsEmailOTP(
                email=request.email, otp=otp, expiry=int(expiry_time)
            )
            db.add(otp_record)

        await db.commit()

        # Send email via AWS SES
        try:
            ses_client = get_ses_client()

            subject = "Verify your email address"
            body = f"Your Turtil OTP is {otp}. Please use this to verify your email address. It is valid for the next 5 minutes."

            response = ses_client.send_email(
                Source="support@turtil.co",  # Must be verified in SES
                Destination={"ToAddresses": [request.email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": body},
                        "Html": {
                            "Data": f"""
                            <html>
                                <body>
                                    <h2>Email Verification</h2>
                                    <p>Your Turtil OTP is <strong>{otp}</strong></p>
                                    <p>Please use this to verify your email address.</p>
                                    <p>This OTP is valid for the next 5 minutes.</p>
                                </body>
                            </html>
                            """
                        },
                    },
                },
            )

            logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")

            return EmailResponse(
                message="OTP sent successfully to your email address", success=True
            )

        except Exception as email_error:
            logger.error(f"Failed to send email: {email_error}")
            # Rollback the database transaction
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email. Please try again later.",
            )

    except Exception as e:
        logger.error(f"Error in send_email_otp: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/verify-otp", response_model=VerifyEmailOTPResponse)
async def verify_email_otp(
    request: VerifyEmailOTPRequest, db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP for email address
    """
    try:
        # Find OTP record for this email
        stmt = select(CmsEmailOTP).where(CmsEmailOTP.email == request.email)
        result = await db.execute(stmt)
        otp_record = result.scalar_one_or_none()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OTP found for this email address",
            )

        # Check if OTP has expired
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        if current_timestamp > otp_record.expiry:
            # Delete expired OTP
            await db.delete(otp_record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

        # Verify OTP
        if str(otp_record.otp) != request.otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP. Please check and try again.",
            )

        # OTP is valid - delete it to prevent reuse
        await db.delete(otp_record)
        await db.commit()

        logger.info(f"Email verified successfully for: {request.email}")

        return VerifyEmailOTPResponse(
            message="Email verified successfully", success=True, email_verified=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_email_otp: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/health")
async def email_health_check():
    """
    Check email service health
    """
    try:
        from app.core.aws import check_aws_health

        aws_health = await check_aws_health()

        return {
            "status": "healthy",
            "services": aws_health,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Email health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
