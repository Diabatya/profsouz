from datetime import date

from models import Member, Payout, PayoutType, Protocol, db


def _make_member(full_name="Тестов Тест Тестович"):
    member = Member(
        full_name=full_name,
        department="Тест",
        birth_date=date(1990, 1, 1),
        entry_date=date(2020, 1, 1),
        status="active",
    )
    db.session.add(member)
    return member


def _make_protocol(number="П-1", pdate=date(2024, 1, 1)):
    protocol = Protocol(number=number, date=pdate, total_amount=0)
    db.session.add(protocol)
    return protocol


def test_protocols_crud(logged_client):
    response = logged_client.get("/protocols/")
    assert response.status_code == 200

    response = logged_client.post(
        "/protocols/add",
        data={"number": "П-2", "date": "2024-04-20", "total_amount": "15000"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    protocol = Protocol.query.filter_by(number="П-2").first()
    assert protocol is not None

    response = logged_client.get(f"/protocols/{protocol.id}")
    assert response.status_code == 200

    response = logged_client.post(f"/protocols/{protocol.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(Protocol, protocol.id) is None


def test_payouts_crud(logged_client):
    member = _make_member()
    ptype = PayoutType.query.filter_by(name="Материальная помощь").first()
    assert ptype is not None
    db.session.commit()
    member_id = member.id
    ptype_id = ptype.id

    response = logged_client.get("/payouts/")
    assert response.status_code == 200

    response = logged_client.post(
        "/payouts/add",
        data={
            "member_id": str(member_id),
            "type_id": str(ptype_id),
            "amount": "5000",
            "date": "2024-07-01",
            "signed": "1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    payout = Payout.query.filter_by(member_id=member_id).first()
    assert payout is not None
    assert payout.type_id == ptype_id
    assert payout.signed is True

    response = logged_client.post(
        f"/payouts/{payout.id}/edit",
        data={
            "member_id": str(member_id),
            "type_id": str(ptype_id),
            "amount": "7500",
            "date": "2024-07-15",
            "signed": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    payout = db.session.get(Payout, payout.id)
    assert float(payout.amount) == 7500
    assert payout.signed is False

    response = logged_client.post(f"/payouts/{payout.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(Payout, payout.id) is None


def test_payouts_export(logged_client):
    member = _make_member()
    ptype = PayoutType.query.filter_by(name="Подарок юбиляру").first()
    assert ptype is not None
    db.session.commit()

    payout = Payout(
        member_id=member.id, type_id=ptype.id, amount=1000, date=date(2024, 1, 1), signed=False
    )
    db.session.add(payout)
    db.session.commit()

    response = logged_client.get("/payouts/export")
    assert response.status_code == 200
    assert (
        response.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
