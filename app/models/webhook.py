from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base


class Webhook(Base):
    __tablename__= "webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    signing_secret = Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_enabled = Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)