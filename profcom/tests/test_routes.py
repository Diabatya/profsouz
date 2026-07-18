from io import BytesIO

from openpyxl import Workbook

from models import Member, db


def test_public_profkom(client):
    response = client.get("/public/profkom")
    assert response.status_code == 200


def test_login_and_dashboard(logged_client):
    response = logged_client.get("/dashboard")
    assert response.status_code == 200


def test_members_index(logged_client):
    response = logged_client.get("/members/")
    assert response.status_code == 200
    assert b"\xd0\xa4\xd0\x98\xd0\x9e" in response.data or b"members" in response.data


def test_member_create_edit_delete(logged_client):
    # create
    response = logged_client.post(
        "/members/add",
        data={
            "full_name": "Тестов Тест Тестович",
            "department": "Тест",
            "position": "Тестер",
            "gender": "auto",
            "birth_date": "1990-01-01",
            "entry_date": "2020-01-01",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    member = Member.query.filter_by(full_name="Тестов Тест Тестович").first()
    assert member is not None
    assert member.gender == "male"

    # edit
    response = logged_client.post(
        f"/members/{member.id}/edit",
        data={
            "full_name": "Тестов Тест Тестович",
            "department": "Тест 2",
            "position": "Тестер",
            "gender": "female",
            "birth_date": "1990-01-01",
            "entry_date": "2020-01-01",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    member = db.session.get(Member, member.id)
    assert member.department == "Тест 2"
    assert member.gender == "female"

    # delete (exclude)
    response = logged_client.post(f"/members/{member.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    member = db.session.get(Member, member.id)
    assert member.status == "not_member"


def test_members_filter_by_gender(logged_client):
    logged_client.post(
        "/members/add",
        data={
            "full_name": "Женский Тест Тестовна",
            "department": "Тест",
            "gender": "auto",
            "birth_date": "1990-01-01",
            "entry_date": "2020-01-01",
        },
        follow_redirects=True,
    )
    response = logged_client.get("/members/?gender=female")
    assert response.status_code == 200
    assert "Женский".encode() in response.data


def test_bulk_exclude(logged_client):
    response = logged_client.post(
        "/members/bulk",
        data={"member_ids": "1,2", "action": "exclude", "value": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_members_export(logged_client):
    response = logged_client.get("/reports/members")
    assert response.status_code == 200
    assert (
        response.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_members_import_update(logged_client):
    # импортируем нового члена
    wb = Workbook()
    ws = wb.active
    ws.append(["ФИО", "Отдел", "Должность", "Пол", "Дата рождения", "Дата вступления"])
    ws.append(
        [
            "Импортов Импорт Импортович",
            "Отдел импорта",
            "Должность",
            "муж",
            "1980-02-02",
            "2019-03-03",
        ]
    )
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = logged_client.post(
        "/members/import",
        data={"file": (buf, "import.xlsx")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    member = Member.query.filter_by(full_name="Импортов Импорт Импортович").first()
    assert member is not None
    assert member.gender == "male"

    # повторный импорт обновляет отдел
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.append(["ФИО", "Отдел", "Должность", "Пол", "Дата рождения", "Дата вступления"])
    ws2.append(
        [
            "Импортов Импорт Импортович",
            "Новый отдел",
            "Новая должность",
            "жен",
            "1980-02-02",
            "2019-03-03",
        ]
    )
    buf2 = BytesIO()
    wb2.save(buf2)
    buf2.seek(0)
    response = logged_client.post(
        "/members/import",
        data={"file": (buf2, "import.xlsx")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    member = Member.query.filter_by(full_name="Импортов Импорт Импортович").first()
    assert member.department == "Новый отдел"
    assert member.gender == "female"
