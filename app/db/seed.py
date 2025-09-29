from app.db.session import SessionLocal
from app.db.models.symbol import Symbol

def seed_symbols():
    db = SessionLocal()
    try:
        tickers = [
            {"ticker": "PETR4.SA", "name": "Petrobras PN", "exchange": "B3", "currency": "BRL"},
            {"ticker": "VALE3.SA", "name": "Vale ON", "exchange": "B3", "currency": "BRL"},
            {"ticker": "ITUB4.SA", "name": "Itaú Unibanco PN", "exchange": "B3", "currency": "BRL"},
        ]
        for t in tickers:
            exists = db.query(Symbol).filter_by(ticker=t["ticker"]).first()
            if not exists:
                db.add(Symbol(**t))
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_symbols()
    print("Seed executado com sucesso!")