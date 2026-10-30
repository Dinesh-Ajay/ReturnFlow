import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple
from app.config import settings
from app.utils.logging_config import logger

class EmailService:
    """
    Sends transactional security emails (OTP verification, recovery alerts)
    via Gmail SMTP with TLS encryption.
    """

    @classmethod
    def send_otp_email(cls, to_email: str, recipient_name: str, otp_code: str) -> Tuple[bool, str]:
        """
        Sends a 6-digit OTP to the recipient's email address.
        Returns (success: bool, message: str).
        """
        if not settings.SMTP_APP_PASSWORD:
            msg = "SMTP_APP_PASSWORD is not configured in .env. Please configure your Gmail App Password."
            logger.warning(f"Email delivery skipped for {to_email}: {msg}")
            return False, msg

        subject = "ReturnFlow Security: Password Reset Verification Code"
        
        # Plain-text version
        plain_body = f"""Hello {recipient_name},

We received a request to reset your ReturnFlow account password.

Your 6-Digit Verification Code: {otp_code}

This code is single-use and will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

Security Warning: Never share this verification code with anyone. ReturnFlow operators will never ask for your code.
If you did not request this password reset, please contact your system administrator immediately.

— ReturnFlow Enterprise Operations Team
"""

        # HTML formatted version
        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
    .container {{ max-width: 540px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .logo {{ display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 700; color: #0F172A; margin-bottom: 24px; }}
    .badge {{ background-color: #2563EB; color: white; border-radius: 6px; padding: 4px 8px; font-size: 14px; font-weight: bold; }}
    .otp-box {{ background: #F1F5F9; border: 2px dashed #CBD5E1; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
    .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #1D4ED8; font-family: monospace; }}
    .warning {{ background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px; font-size: 12px; color: #991B1B; border-radius: 4px; margin-top: 20px; }}
    .footer {{ margin-top: 32px; font-size: 11px; color: #94A3B8; text-align: center; border-top: 1px solid #F1F5F9; padding-top: 16px; }}
</style>
</head>
<body>
<div class="container">
    <div class="logo">
        <span class="badge">&#9632;</span> ReturnFlow Enterprise
    </div>
    <h2 style="font-size: 18px; margin-top: 0; color: #0F172A;">Password Reset Verification</h2>
    <p style="font-size: 14px; color: #475569; line-height: 1.5;">
        Hello <strong>{recipient_name}</strong>,<br>
        A request has been initiated to reset the password for your ReturnFlow account (<code>{to_email}</code>).
    </p>
    <div class="otp-box">
        <div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 600; margin-bottom: 4px;">One-Time Verification Code</div>
        <div class="otp-code">{otp_code}</div>
        <div style="font-size: 12px; color: #64748B; margin-top: 6px;">Valid for <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong></div>
    </div>
    <div class="warning">
        <strong>Security Notice:</strong> Do not share this code with anyone. ReturnFlow support staff will never ask for your verification code.
    </div>
    <p style="font-size: 13px; color: #64748B; margin-top: 20px;">
        If you did not initiate this request, you can safely disregard this email. Your current password remains active and secure.
    </p>
    <div class="footer">
        &copy; 2026 ReturnFlow Lifecycle Management Systems. All rights reserved.
    </div>
</div>
</body>
</html>
"""

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"ReturnFlow Security <{settings.SMTP_EMAIL}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            logger.info(f"Connecting to SMTP server {settings.SMTP_SERVER}:{settings.SMTP_PORT} via TLS...")
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.SMTP_EMAIL, settings.SMTP_APP_PASSWORD)
                server.sendmail(settings.SMTP_EMAIL, [to_email], msg.as_string())

            logger.info(f"Password reset OTP successfully emailed to {to_email}")
            return True, "Verification code sent to registered email address."

        except smtplib.SMTPAuthenticationError as e:
            err_msg = "SMTP Authentication failed: check SMTP_EMAIL and SMTP_APP_PASSWORD in .env."
            logger.error(f"{err_msg} Details: {e}")
            return False, err_msg
        except smtplib.SMTPConnectError as e:
            err_msg = f"Failed to connect to SMTP server {settings.SMTP_SERVER}:{settings.SMTP_PORT}."
            logger.error(f"{err_msg} Details: {e}")
            return False, err_msg
        except Exception as e:
            err_msg = f"Failed to deliver verification email: {str(e)}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg
