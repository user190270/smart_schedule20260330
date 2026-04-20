from __future__ import annotations

from sqlalchemy import text

from app.core.database import SessionLocal, init_db


def reset_database() -> None:
    init_db()
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE email_reminders, knowledge_base_states, share_links, vector_chunks, chat_history, schedules, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()
