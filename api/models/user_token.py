"""UserToken — revocable JWT tracking for user sessions.

Every access token and refresh token issued to a user gets one row.
The jti claim in the JWT payload is the join key. On every authenticated
request the middleware checks: jti in user_tokens AND revoked_at IS NULL.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, String, TIMESTAMP
from sqlalchemy.sql import func

from db.connection import Base

# Token type constants — only these two values are allowed.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class UserToken(Base):
    __tablename__ = "user_tokens"

    __table_args__ = (
        Index("idx_user_tokens_user_id", "user_id"),
        Index("idx_user_tokens_expires_at", "expires_at"),
        Index("idx_user_tokens_revoked_at", "revoked_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True)

    # UUID v4 embedded as the "jti" claim in the JWT payload.
    jti = Column(String(36), unique=True, nullable=False, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "access" | "refresh"
    token_type = Column(String(16), nullable=False)

    issued_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)

    # Non-null when the token has been explicitly revoked (logout / rotation).
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Set during refresh rotation: jti of the successor token.
    replaced_by_jti = Column(String(36), nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
