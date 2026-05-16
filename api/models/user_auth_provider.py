from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from db import Base


class UserAuthProvider(Base):
    __tablename__ = "user_auth_providers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)       # 'web3', 'email', 'google', 'microsoft'
    provider_id = Column(String(256), nullable=False)   # wallet / email / oauth sub / oid
    password_hash = Column(String, nullable=True)       # only for 'email' provider
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_user_auth_providers_provider_id"),
    )
