import os
import tempfile
from datetime import date

import pytest

os.environ["PROFCOM_SKIP_INIT"] = "1"

from app import app, seed_data  # noqa: E402
from models import Admin, Member, PayoutType, Protocol, db  # noqa: E402


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        # пересоздаём engine, чтобы использовать временную БД
        db.session.remove()
        if db.engines:
            try:
                db.engines[None].dispose()
            except Exception:
                pass
        db.engines[None] = db._make_engine(
            None, {"url": app.config["SQLALCHEMY_DATABASE_URI"]}, app
        )
        db.create_all()
        seed_data()

        with app.test_client() as test_client:
            yield test_client

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def logged_client(client):
    admin = Admin.query.filter_by(username="admin").first()
    with client.session_transaction() as sess:
        sess["admin_id"] = admin.id
    return client


@pytest.fixture
def sample_member(client):
    member = Member(
        full_name="Фикстурный Тест Тестович",
        department="Тест",
        birth_date=date(1990, 1, 1),
        entry_date=date(2020, 1, 1),
        status="active",
    )
    db.session.add(member)
    db.session.commit()
    return member.id


@pytest.fixture
def sample_protocol(client):
    protocol = Protocol(number="П-Ф", date=date(2024, 1, 1), total_amount=0)
    db.session.add(protocol)
    db.session.commit()
    return protocol.id


@pytest.fixture
def sample_payout_type(client):
    ptype = PayoutType(name="Тип фикстуры", default_amount=100)
    db.session.add(ptype)
    db.session.commit()
    return ptype.id
