from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AiUsageEvent, User
from app.models.enums import SubscriptionTier
from app.services.ai_runtime import TokenUsage


@dataclass(frozen=True)
class QuotaSnapshot:
    subscription_tier: SubscriptionTier
    daily_token_usage: int
    daily_token_limit: int


class QuotaExceededError(RuntimeError):
    def __init__(self, snapshot: QuotaSnapshot):
        super().__init__("Today's token quota has been exhausted for the current tier.")
        self.snapshot = snapshot

    def to_http_detail(self) -> dict[str, object]:
        return {
            "error_code": "daily_token_quota_exceeded",
            "message": str(self),
            "subscription_tier": self.snapshot.subscription_tier.value,
            "daily_token_usage": self.snapshot.daily_token_usage,
            "daily_token_limit": self.snapshot.daily_token_limit,
        }


class QuotaService:
    _TIER_ORDER = [
        SubscriptionTier.FREE,
        SubscriptionTier.PLUS,
        SubscriptionTier.PRO,
    ]
    _DAILY_LIMITS = {
        SubscriptionTier.FREE: 5_000,
        SubscriptionTier.PLUS: 20_000,
        SubscriptionTier.PRO: 50_000,
    }

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _local_timezone() -> ZoneInfo:
        timezone_name = getattr(get_settings(), "app_timezone", "Asia/Shanghai") or "Asia/Shanghai"
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("Asia/Shanghai")

    @classmethod
    def _local_day(cls, value: datetime) -> date:
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(cls._local_timezone()).date()

    @classmethod
    def get_daily_limit(cls, tier: SubscriptionTier | None) -> int:
        resolved_tier = tier or SubscriptionTier.FREE
        return cls._DAILY_LIMITS[resolved_tier]

    @classmethod
    def _snapshot_from_user(cls, user: User) -> QuotaSnapshot:
        tier = user.subscription_tier or SubscriptionTier.FREE
        return QuotaSnapshot(
            subscription_tier=tier,
            daily_token_usage=int(user.daily_token_usage),
            daily_token_limit=cls.get_daily_limit(tier),
        )

    @classmethod
    def reset_usage_if_new_day(cls, user: User, *, now: datetime | None = None) -> bool:
        current_time = now or cls._utc_now()
        last_reset = user.last_reset_time if user.last_reset_time.tzinfo is not None else user.last_reset_time.replace(
            tzinfo=timezone.utc
        )
        if cls._local_day(last_reset) == cls._local_day(current_time):
            return False
        user.daily_token_usage = 0
        user.last_reset_time = current_time
        return True

    @staticmethod
    def get_active_user(db: Session, user_id: int) -> User | None:
        return db.scalar(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )

    @classmethod
    def sync_quota_window(cls, db: Session, user: User, *, now: datetime | None = None) -> QuotaSnapshot:
        changed = cls.reset_usage_if_new_day(user, now=now)
        if changed:
            db.add(user)
            db.commit()
            db.refresh(user)
        return cls._snapshot_from_user(user)

    @classmethod
    def get_quota_snapshot(cls, db: Session, user_id: int, *, now: datetime | None = None) -> QuotaSnapshot | None:
        user = cls.get_active_user(db, user_id)
        if user is None:
            return None
        return cls.sync_quota_window(db, user, now=now)

    @classmethod
    def ensure_token_quota_available(cls, db: Session, user_id: int, *, now: datetime | None = None) -> QuotaSnapshot:
        user = cls.get_active_user(db, user_id)
        if user is None:
            raise LookupError("User not found or inactive.")
        snapshot = cls.sync_quota_window(db, user, now=now)
        if snapshot.daily_token_usage >= snapshot.daily_token_limit:
            raise QuotaExceededError(snapshot)
        return snapshot

    @classmethod
    def record_token_usage(
        cls,
        db: Session,
        user_id: int,
        *,
        operation: str,
        usage: TokenUsage,
        model_name: str | None = None,
        now: datetime | None = None,
    ) -> QuotaSnapshot:
        user = cls.get_active_user(db, user_id)
        if user is None:
            raise LookupError("User not found or inactive.")

        current_time = now or cls._utc_now()
        cls.reset_usage_if_new_day(user, now=current_time)

        total_tokens = max(0, int(usage.total_tokens))
        if total_tokens <= 0:
            db.add(user)
            db.commit()
            db.refresh(user)
            return cls._snapshot_from_user(user)

        user.daily_token_usage += total_tokens
        db.add(
            AiUsageEvent(
                user_id=user.id,
                operation=operation,
                model_name=model_name,
                input_tokens=max(0, int(usage.input_tokens)),
                output_tokens=max(0, int(usage.output_tokens)),
                total_tokens=total_tokens,
                created_at=current_time,
            )
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return cls._snapshot_from_user(user)

    @classmethod
    def resolve_upgrade_target(
        cls,
        current_tier: SubscriptionTier | None,
        requested_tier: SubscriptionTier | None,
    ) -> SubscriptionTier:
        resolved_current = current_tier or SubscriptionTier.FREE
        current_index = cls._TIER_ORDER.index(resolved_current)

        if requested_tier is None:
            if current_index >= len(cls._TIER_ORDER) - 1:
                raise ValueError("Current demo tier is already the highest available tier.")
            return cls._TIER_ORDER[current_index + 1]

        target_index = cls._TIER_ORDER.index(requested_tier)
        if target_index <= current_index:
            raise ValueError("Demo upgrade target must be higher than the current tier.")
        return requested_tier
