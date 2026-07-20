from flask import Blueprint, render_template, request

from models import Member, Payout, PayoutType
from utils import login_required, parse_date

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
def index():
    return render_template("reports/index.html")


@bp.route("/payouts")
@login_required
def payouts_report():
    from utils import excel_response

    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    q = Payout.query.join(Member).join(PayoutType)
    if date_from:
        q = q.filter(Payout.date >= date_from)
    if date_to:
        q = q.filter(Payout.date <= date_to)

    headers = ["Дата", "Член", "Тип", "Протокол", "Сумма", "Подписана"]
    rows = []
    for p in q.order_by(Payout.date.desc()).all():
        rows.append(
            [
                p.date.strftime("%d.%m.%Y"),
                p.member.full_name,
                p.type.name,
                p.protocol.number if p.protocol else "",
                float(p.amount),
                "Да" if p.signed else "Нет",
            ]
        )
    return excel_response(headers, rows, "otchet_viplaty.xlsx")


@bp.route("/material_aid")
@login_required
def material_aid_report():
    from utils import excel_response

    ptype = PayoutType.query.filter_by(name="Материальная помощь").first()
    if not ptype:
        ptype = PayoutType.query.first()
    q = Payout.query.join(Member).filter(Payout.type_id == ptype.id) if ptype else Payout.query
    rows = []
    for p in q.order_by(Payout.date.desc()).all():
        rows.append(
            [
                p.date.strftime("%d.%m.%Y"),
                p.member.full_name,
                p.member.department,
                float(p.amount),
                "Да" if p.signed else "Нет",
            ]
        )
    headers = ["Дата", "Член", "Отдел", "Сумма", "Подписана"]
    return excel_response(headers, rows, "otchet_materialnaya_pomoshch.xlsx")


@bp.route("/members")
@login_required
def members_report():
    from utils import excel_response

    members = Member.query.order_by(Member.full_name).all()
    headers = [
        "ФИО",
        "Отдел",
        "Должность",
        "Пол",
        "Дата рождения",
        "Дата вступления",
        "Статус",
        "Группы",
    ]
    rows = []
    for m in members:
        groups = ", ".join([g.name for g in m.groups])
        status = "Активен" if m.status == "active" else "Не член"
        rows.append(
            [
                m.full_name,
                m.department,
                m.position or "",
                m.gender_display,
                m.birth_date.strftime("%d.%m.%Y") if m.birth_date else "",
                m.entry_date.strftime("%d.%m.%Y") if m.entry_date else "",
                status,
                groups,
            ]
        )
    return excel_response(headers, rows, "spisok_chlenov.xlsx")
