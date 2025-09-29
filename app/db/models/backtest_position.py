from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from app.db.base import Base

class BacktestPosition(Base):
    __tablename__ = "backtest_positions"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id"), nullable=False)
    date = Column(Date, nullable=False)
    position = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)