"""RequestNonce — idempotency-key store for sensitive mutation endpoints.

A duplicate nonce for the same endpoint returns HTTP 409 Conflict.
Rows older than 24 h are cleaned up opportunistically by the
require_idempotency_key dependency on each request.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from db.connection import Base


class RequestNonce(Base):
    __tablename__ = "request_nonces"

    __table_args__ = (
        Index("idx_request_nonces_user_id", "user_id"),
        Index("idx_request_nonces_created_at", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True)

    # UUID v4 from the Idempotency-Key request header.
    nonce = Column(String(36), unique=True, nullable=False, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    endpoint = Column(Text, nullable=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
