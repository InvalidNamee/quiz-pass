import json

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(self, actor_user_id: int | None, action: str, target_type: str, target_id: int | None, metadata: dict | None = None) -> AuditEvent:
        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self.db.add(event)
        self.db.flush()
        return event
