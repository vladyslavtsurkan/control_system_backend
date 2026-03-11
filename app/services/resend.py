import aiohttp

from app.core import settings
from app.core.decorators import retry


class ResendException(Exception):
    pass


class ResendService:
    def __init__(self):
        self._config = settings.resend

    @retry(max_retries=3)
    async def _send_email(self, recipient: str, subject: str, content: str) -> None:
        payload = self._format_email(recipient, subject, content)
        headers = {"Authorization": f"Bearer {self._config.API_KEY}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self._config.API_URL}/emails", headers=headers, json=payload) as response:
                if response.status != 200:
                    raise ResendException(f"Failed to send email: {await response.text()}")

    def _format_email(self, recipient: str, subject: str, content: str) -> dict:
        return {
            "from": self._config.FROM_EMAIL,
            "to": [recipient],
            "subject": subject,
            "html": content,
        }

    async def send_verification_code_email(self, recipient: str, code: str) -> None:
        subject = "Your Verification Code - Control System"
        content = f"<p>Your verification code is <strong>{code}</strong>.</p>"
        await self._send_email(recipient, subject, content)

    async def send_reset_password_email(self, recipient: str, code: str) -> None:
        subject = "Reset Your Password - Control System"
        content = f"<p>To reset your password, use the following code: <strong>{code}</strong>.</p>"
        await self._send_email(recipient, subject, content)


resend_service = ResendService()
