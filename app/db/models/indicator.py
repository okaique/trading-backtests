from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    date = Column(Date, nullable=False)
    name = Column(String, nullable=False)   # ex: SMA
    value = Column(Float, nullable=False)
    params = Column(String, nullable=True)  # ex: {"window":20}

    __table_args__ = (
        UniqueConstraint("symbol_id", "date", "name", "params", name="uq_indicator"),
    )

    symbol = relationship("Symbol", backref="indicators")