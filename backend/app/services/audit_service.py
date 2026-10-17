"""Append audit events in the business transaction; never commit independently."""
from app.models.models import AuditLog

def audit(db, tenant_id, actor, action, entity_type, entity_id, details=None):
    db.add(AuditLog(tenant_id=tenant_id, actor_id=actor.id if actor else None,
                    action=action, entity_type=entity_type, entity_id=entity_id,
                    details=details or {}))
