from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import KnowledgeBaseState, Schedule, VectorChunk
from app.schemas import SyncPushRequest, SyncPushResultItem, SyncStatusResponse
from app.services.email_reminder_service import EmailReminderService


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SyncService:
    @staticmethod
    def push_schedules(db: Session, user_id: int, payload: SyncPushRequest) -> list[SyncPushResultItem]:
        results: list[SyncPushResultItem] = []
        affected_schedule_ids: set[int] = set()

        for record in payload.records:
            existing_for_user: Schedule | None = None
            existing_by_id: Schedule | None = None

            if record.id is not None:
                existing_by_id = db.scalar(select(Schedule).where(Schedule.id == record.id))
                if existing_by_id is not None and existing_by_id.user_id != user_id:
                    results.append(
                        SyncPushResultItem(
                            schedule_id=record.id,
                            status="ignored",
                            reason="record id belongs to another user",
                        )
                    )
                    continue
                existing_for_user = existing_by_id

            incoming_updated_at = _as_utc(record.updated_at)

            if existing_for_user is None:
                created = Schedule(
                    id=record.id,
                    user_id=user_id,
                    title=record.title,
                    start_time=record.start_time,
                    end_time=record.end_time,
                    location=record.location,
                    remark=record.remark,
                    source=record.source,
                    updated_at=incoming_updated_at,
                    allow_rag_indexing=record.allow_rag_indexing,
                    email_reminder_enabled=record.email_reminder_enabled,
                    email_remind_before_minutes=record.email_remind_before_minutes,
                    is_deleted=record.is_deleted,
                )
                db.add(created)
                db.flush()
                affected_schedule_ids.add(created.id)
                results.append(SyncPushResultItem(schedule_id=created.id, status="created"))
                continue

            existing_updated_at = _as_utc(existing_for_user.updated_at)
            if incoming_updated_at <= existing_updated_at:
                results.append(
                    SyncPushResultItem(
                        schedule_id=existing_for_user.id,
                        status="ignored",
                        reason="incoming record is not newer than server record",
                    )
                )
                continue

            existing_for_user.title = record.title
            existing_for_user.start_time = record.start_time
            existing_for_user.end_time = record.end_time
            existing_for_user.location = record.location
            existing_for_user.remark = record.remark
            existing_for_user.source = record.source
            existing_for_user.allow_rag_indexing = record.allow_rag_indexing
            existing_for_user.email_reminder_enabled = record.email_reminder_enabled
            existing_for_user.email_remind_before_minutes = record.email_remind_before_minutes
            existing_for_user.is_deleted = record.is_deleted
            existing_for_user.updated_at = incoming_updated_at
            affected_schedule_ids.add(existing_for_user.id)
            results.append(SyncPushResultItem(schedule_id=existing_for_user.id, status="updated"))

        db.commit()
        for schedule_id in affected_schedule_ids:
            EmailReminderService.sync_schedule_by_id(db, schedule_id)
        if affected_schedule_ids:
            db.commit()
        return results

    @staticmethod
    def pull_schedules(db: Session, user_id: int, since: datetime | None) -> list[Schedule]:
        statement = select(Schedule).where(Schedule.user_id == user_id)
        if since is not None:
            statement = statement.where(Schedule.updated_at > _as_utc(since))
        statement = statement.order_by(Schedule.updated_at.asc(), Schedule.id.asc())
        return list(db.scalars(statement).all())

    @staticmethod
    def get_status(db: Session, user_id: int) -> SyncStatusResponse:
        cloud_schedule_count = int(
            db.scalar(
                select(func.count())
                .select_from(Schedule)
                .where(Schedule.user_id == user_id, Schedule.is_deleted.is_(False))
            )
            or 0
        )

        knowledge_base_eligible_schedule_count = int(
            db.scalar(
                select(func.count())
                .select_from(Schedule)
                .where(
                    Schedule.user_id == user_id,
                    Schedule.is_deleted.is_(False),
                    Schedule.allow_rag_indexing.is_(True),
                )
            )
            or 0
        )

        indexed_schedule_count = int(
            db.scalar(
                select(func.count(distinct(VectorChunk.schedule_id)))
                .select_from(VectorChunk)
                .join(Schedule, Schedule.id == VectorChunk.schedule_id)
                .where(
                    VectorChunk.user_id == user_id,
                    Schedule.user_id == user_id,
                    Schedule.is_deleted.is_(False),
                    Schedule.allow_rag_indexing.is_(True),
                )
            )
            or 0
        )

        indexed_chunk_count = int(
            db.scalar(
                select(func.count(VectorChunk.id))
                .select_from(VectorChunk)
                .join(Schedule, Schedule.id == VectorChunk.schedule_id)
                .where(
                    VectorChunk.user_id == user_id,
                    Schedule.user_id == user_id,
                    Schedule.is_deleted.is_(False),
                    Schedule.allow_rag_indexing.is_(True),
                )
            )
            or 0
        )

        kb_state = db.scalar(select(KnowledgeBaseState).where(KnowledgeBaseState.user_id == user_id))
        settings = get_settings()

        return SyncStatusResponse(
            cloud_schedule_count=cloud_schedule_count,
            knowledge_base_eligible_schedule_count=knowledge_base_eligible_schedule_count,
            indexed_schedule_count=indexed_schedule_count,
            indexed_chunk_count=indexed_chunk_count,
            last_knowledge_rebuild_at=kb_state.last_rebuild_at if kb_state else None,
            last_knowledge_rebuild_status=kb_state.last_rebuild_status if kb_state and kb_state.last_rebuild_status else "idle",
            last_knowledge_rebuild_message=kb_state.last_rebuild_message if kb_state else None,
            last_knowledge_rebuild_schedules_considered=kb_state.last_rebuild_schedules_considered if kb_state else 0,
            last_knowledge_rebuild_schedules_indexed=kb_state.last_rebuild_schedules_indexed if kb_state else 0,
            last_knowledge_rebuild_chunks_created=kb_state.last_rebuild_chunks_created if kb_state else 0,
            embedding_dimensions=kb_state.embedding_dimensions if kb_state and kb_state.embedding_dimensions else settings.embedding_dimensions,
            cloud_connection_status="connected",
        )

