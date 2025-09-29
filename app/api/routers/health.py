import time
import yfinance as yf
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
def health_check():
    db = SessionLocal()
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_ok = True
        db_latency = round((time.time() - start) * 1000, 2)
    except SQLAlchemyError:
        db_ok = False
        db_latency = None
    finally:
        db.close()

    start = time.time()
    try:
        yf.Ticker("PETR4.SA").history(period="1d")
        yahoo_ok = True
        yahoo_latency = round((time.time() - start) * 1000, 2)
    except Exception:
        yahoo_ok = False
        yahoo_latency = None

    return {
        "db_ok": db_ok,
        "db_latency_ms": db_latency,
        "yahoo_ok": yahoo_ok,
        "yahoo_latency_ms": yahoo_latency,
    }