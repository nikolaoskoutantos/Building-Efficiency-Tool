"""idempotency.py — FastAPI dependency for sensitive mutation endpoints.

Sensitive endpoints (device commands, optimization triggers, config updates)
must include an `Idempotency-Key: <uuid>` header.  Duplicate keys for the
same endpoint return HTTP 409 Conflict.

Rows older than 24 h are purged opportunistically on every request so the
table stays small without requiring a separate cron job.

Usage:
    from utils.idempotency import require_idempotency_key

    @router.post("/devices/{id}/command")
    def send_command(
        ...,
        _: None = Depends(require_idempotency_key),
    ):
        ...
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from db.connection import get_db
from models.request_nonce import RequestNonce

# How long a nonce is retained before it can be garbage-collected.
NONCE_TTL_HOURS = 24


def require_idempotency_key(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> str:
    """Dependency that enforces a unique Idempotency-Key on each request.

    Steps:
    1. Reject if the header is missing.
    2. Reject if the header value is not a valid UUID v4.
    3. Opportunistically delete nonces older than NONCE_TTL_HOURS.
    4. Return HTTP 409 if the nonce already exists for this endpoint.
    5. Insert the nonce and return it.

    Returns:
        The validated idempotency key string (so endpoints can include it
        in their response if desired).
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key header is required for this endpoint",
        )

    try:
        uuid.UUID(idempotency_key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key must be a valid UUID v4",
        )

    endpoint = str(request.url.path)

    # Opportunistic cleanup — keeps the table tiny without a cron job.
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NONCE_TTL_HOURS)
    db.query(RequestNonce).filter(RequestNonce.created_at < cutoff).delete(
        synchronize_session=False
    )

    existing = (
        db.query(RequestNonce)
        .filter(RequestNonce.nonce == idempotency_key)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate request: this Idempotency-Key has already been processed",
        )

    # Resolve user_id from JWT if present — best-effort, not required.
    user_id: Optional[int] = _extract_user_id(request)

    db.add(RequestNonce(
        nonce=idempotency_key,
        user_id=user_id,
        endpoint=endpoint,
    ))
    db.commit()

    return idempotency_key


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_user_id(request: Request) -> Optional[int]:
    """Best-effort extraction of user_id from Bearer token — never raises."""
    try:
        import jwt as _jwt
        import os
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        secret = os.environ.get("SESSION_SECRET_KEY", "")
        if not secret:
            return None
        payload = _jwt.decode(token, secret, algorithms=["HS256"])
        uid = payload.get("user_id")
        return int(uid) if uid is not None else None
    except Exception:
        return None
