from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.core.config import get_settings
from app.models import Schedule


class MailConfigurationError(RuntimeError):
    pass


class MailDeliveryError(RuntimeError):
    pass


class MailService:
    BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"

    @staticmethod
    def is_configured() -> bool:
        settings = get_settings()
        return bool(
            settings.mail_provider == "brevo"
            and settings.mail_api_key
            and settings.mail_from_address
        )

    @staticmethod
    def _format_local_schedule_time(start_time: datetime | None, end_time: datetime | None) -> str:
        if start_time is None:
            return "待定"

        settings = get_settings()
        tz = ZoneInfo(settings.app_timezone)
        start_local = start_time.astimezone(tz)
        if end_time is None:
            return start_local.strftime("%Y-%m-%d %H:%M")

        end_local = end_time.astimezone(tz)
        if start_local.date() == end_local.date():
            return f"{start_local.strftime('%Y-%m-%d %H:%M')} - {end_local.strftime('%H:%M')}"
        return f"{start_local.strftime('%Y-%m-%d %H:%M')} - {end_local.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    async def send_schedule_reminder(
        cls,
        *,
        to_email: str,
        schedule: Schedule,
        lead_minutes: int,
    ) -> str | None:
        settings = get_settings()
        if settings.mail_provider != "brevo":
            raise MailConfigurationError("MAIL_PROVIDER must be set to brevo")
        if not settings.mail_api_key or not settings.mail_from_address:
            raise MailConfigurationError("MAIL_API_KEY and MAIL_FROM_ADDRESS must be configured")

        schedule_time = cls._format_local_schedule_time(schedule.start_time, schedule.end_time)
        location_line = schedule.location or "未设置地点"
        lead_line = "开始时提醒" if lead_minutes == 0 else f"提前 {lead_minutes} 分钟提醒"
        remark_line = schedule.remark.strip() if schedule.remark else ""

        text_lines = [
            f"日程提醒：{schedule.title}",
            f"时间：{schedule_time}",
            f"地点：{location_line}",
            f"提醒设置：{lead_line}",
        ]
        if remark_line:
            text_lines.append(f"备注：{remark_line}")

        payload = {
            "sender": {
                "email": settings.mail_from_address,
                "name": settings.mail_from_name,
            },
            "to": [{"email": to_email}],
            "subject": f"日程提醒：{schedule.title}",
            "textContent": "\n".join(text_lines),
        }

        headers = {
            "accept": "application/json",
            "api-key": settings.mail_api_key,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(cls.BREVO_SEND_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json() if response.content else {}
        except httpx.HTTPError as exc:
            raise MailDeliveryError(str(exc)) from exc

        message_id = data.get("messageId")
        if isinstance(message_id, list):
            return str(message_id[0]) if message_id else None
        if message_id is None:
            return None
        return str(message_id)
