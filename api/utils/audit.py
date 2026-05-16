"""audit.py — immutable audit trail helper for all auth events.

Usage:
    from utils.audit import log_event, get_client_ip

    log_event(
        db=db,
        event_type="login_success",
        success=True,
        user_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details={"wallet": "0xabc...", "jti": access_jti},
    )
    db.commit()   # caller owns the transaction

Event type constants are defined below. Use them instead of raw strings to
prevent typos and make grep-based forensic queries reliable.
"""

import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from models.auth_audit_log import AuthAuditLog

logger = logging.getLogger("auth_audit")

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

EVENT_LOGIN_SUCCESS = "login_success"
EVENT_LOGIN_FAILURE = "login_failure"
EVENT_LOGOUT = "logout"
EVENT_LOGOUT_ALL = "logout_all"
EVENT_REFRESH_SUCCESS = "refresh_success"
EVENT_REFRESH_FAILURE = "refresh_failure"
EVENT_TOKEN_REVOKED = "token_revoked"
EVENT_TOKEN_REUSE = "token_reuse_detected"          # stolen refresh token reused
EVENT_REPLAY_DETECTED = "replay_detected"           # idempotency-key collision
EVENT_INVALID_TOKEN = "invalid_token"
EVENT_NONCE_REJECTED = "nonce_rejected"             # Web3 nonce replay / stale
EVENT_MQTT_REPLAY = "mqtt_replay_detected"          # duplicate msg_id from device
EVENT_MQTT_STALE = "mqtt_stale_timestamp"           # MQTT message outside time window


# ---------------------------------------------------------------------------
# IP extraction — respects X-Forwarded-For set by Traefik
# ---------------------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For may be a comma-separated chain; first entry is the
        # real client IP when Traefik is configured to append, not replace.
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# Core logging helper
# ---------------------------------------------------------------------------

def log_event(
    db: Session,
    event_type: str,
    success: bool = True,
    user_id: Optional[int] = None,
    device_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Write one row to auth_audit_log.

    Uses db.flush() so the insert participates in the caller's transaction.
    The caller must call db.commit() (or rollback) afterwards.

    Failures are caught and logged to the Python logger so that an audit
    write error never breaks the primary auth flow.
    """
    try:
        entry = AuthAuditLog(
            user_id=user_id,
            device_id=device_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details,
        )
        db.add(entry)
        db.flush()
    except Exception:
        logger.exception(
            "Failed to write audit log event_type=%s user_id=%s",
            event_type, user_id,
        )


def log_event_commit(
    db: Session,
    event_type: str,
    success: bool = True,
    user_id: Optional[int] = None,
    device_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Same as log_event but commits immediately.

    Use this when you need the audit row persisted even if the outer
    transaction rolls back (e.g., logging a failed login attempt).
    """
    try:
        entry = AuthAuditLog(
            user_id=user_id,
            device_id=device_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to write audit log (commit) event_type=%s user_id=%s",
            event_type, user_id,
        )
