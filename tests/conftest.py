import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import SessionLocal
from app.db.models.symbol import Symbol
from app.db.models.price import Price
from app.db.models.indicator import Indicator


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def seed_symbol(db_session):
    symbol = Symbol(ticker="PETR4.SA", name="Petrobras", exchange="B3", currency="BRL")
    db_session.add(symbol)
    db_session.commit()
    return symbol