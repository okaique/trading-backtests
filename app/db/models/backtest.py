from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False)
    strategy_type = Column(String, nullable=False, default="sma_cross")
    strategy_params = Column(JSON, nullable=True)
    fast_period = Column(Integer, nullable=True)
    slow_period = Column(Integer, nullable=True)
    start = Column(String, nullable=True)
    end = Column(String, nullable=True)
    initial_cash = Column(Float, nullable=False)
    final_value = Column(Float, nullable=True)
    status = Column(String, default="completed")
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())