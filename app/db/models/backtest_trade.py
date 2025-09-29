from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from app.db.base import Base

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id"), nullable=False)
    date = Column(Date, nullable=False)
    operation = Column(String, nullable=False)  # buy/sell
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)