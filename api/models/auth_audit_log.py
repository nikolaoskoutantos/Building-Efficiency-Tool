"""AuthAuditLog — immutable audit trail for all authentication events.

Never delete rows from this table. Use for forensic analysis and security
monitoring. All auth events (login, logout, refresh, revocation, replay
detection) are written here by the audit helper in utils/audit.py.
"""
from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Index, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from db.connection import Base


class AuthAuditLog(Base):
    __tablename__ = "auth_audit_log"

    __table_args__ = (
        Index("idx_auth_audit_log_user_id", "user_id"),
        Index("idx_auth_audit_log_event_type", "event_type"),
        Index("idx_auth_audit_log_created_at", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True)

    # Nullable: unauthenticated events (failed login) may not have a user.
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Nullable: only populated for device-related auth events.
    device_id = Column(
        BigInteger,
        ForeignKey("hvac_units.id", ondelete="SET NULL"),
        nullable=True,
    )

    # e.g. "login_success", "login_failure", "logout", "token_reuse_detected"
    event_type = Column(String(64), nullable=False)

    # Real client IP (X-Forwarded-For respected for Traefik).
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)

    success = Column(Boolean, nullable=False, server_default="true")

    # Flexible JSON payload for event-specific details (jti, wallet, reason …).
    details = Column(JSONB, nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
