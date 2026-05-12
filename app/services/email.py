import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

logger = logging.getLogger(__name__)

_conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.EMAILS_FROM,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


async def send_password_reset_email(email: str, reset_token: str) -> None:
    reset_url = f"{settings.API_URL}/auth/reset-password?token={reset_token}"
    body = f"""
    <h2>Password Reset Request</h2>
    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
    <a href="{reset_url}" style="
        display: inline-block;
        padding: 12px 24px;
        background: #0ea5e9;
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
    ">Reset Password</a>
    <p>If you did not request this, you can safely ignore this email.</p>
    <p style="color: #64748b; font-size: 12px;">This link will expire in 1 hour.</p>
    """
    message = MessageSchema(
        subject="Reset your BoltLink password",
        recipients=[email],
        body=body,
        subtype=MessageType.html,
    )
    try:
        fm = FastMail(_conf)
        await fm.send_message(message)
        logger.info("email.reset_sent recipient=%s", email)
    except Exception as e:
        logger.error(
            "email.reset_failed recipient=%s error=%s", email, e, exc_info=True
        )
        raise
