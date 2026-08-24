from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey, DateTime, JSON

from app.models.base import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    warehouse_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    data_json: Mapped[dict] = mapped_column(JSON, default=dict)
