from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request, url_for
from sqlalchemy import extract

from models import FinanceMonth, FinanceYear, Member, MemberChild, Payout, PayoutType, Protocol, db
from utils import login_required, parse_date

MONTH_NAMES = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]

bp = Blueprint("main", __name__)


def _current_year_finance():
    current_year = date.today().year
    year = FinanceYear.query.filter_by(year=current_year).first()
    result = {"income": Decimal(0), "expenses": Decimal(0), "balance": Decimal(0)}
    if not year:
        return result
    income = sum((m.gross_amount for m in year.months.all()), Decimal(0))
    expenses = sum((e.amount for e in year.expenses.all()), Decimal(0))
    commissions = sum((c.amount for c in year.commissions.all()), Decimal(0))
    result["income"] = income
    result["expenses"] = expenses
    result["balance"] = year.ppo_opening + year.charity_opening + income - expenses - commissions
    return result


@bp.route("/dashboard")
@login_required
def dashboard():
    total_members = Member.query.filter(Member.status != "excluded").count()
    protocols_this_year = Protocol.query.filter(extract("year", Protocol.date) == date.today().year).count()
    total_payouts = Payout.query.count()
    members_by_department = (
        db.session.query(Member.department, db.func.count(Member.id))
        .filter(Member.status != "excluded")
        .group_by(Member.department)
        .order_by(db.func.count(Member.id).desc())
        .all()
    )
    finance = _current_year_finance()

    timeline = []
    for protocol in Protocol.query.order_by(Protocol.date.desc()).limit(8).all():
        timeline.append(
            {
                "type": "protocol",
                "date": protocol.date,
                "title": f"Протокол №{protocol.number}",
                "url": url_for("protocols.detail", id=protocol.id),
                "amount": protocol.total_amount,
            }
        )
    for payout in Payout.query.order_by(Payout.date.desc()).limit(8).all():
        timeline.append(
            {
                "type": "payout",
                "date": payout.date,
                "title": f"Выплата {payout.member.full_name} ({payout.type.name})",
                "url": url_for("payouts.index"),
                "amount": payout.amount,
            }
        )
    for fm in FinanceMonth.query.order_by(FinanceMonth.date_received.desc()).limit(8).all():
        timeline.append(
            {
                "type": "income",
                "date": fm.date_received or date(fm.year.year, fm.month, 1),
                "title": f"Приход за {fm.month}.{fm.year.year}",
                "url": url_for("finances.index", year_id=fm.year_id),
                "amount": fm.gross_amount,
            }
        )
    timeline.sort(key=lambda x: x["date"], reverse=True)
    timeline = timeline[:15]

    attention = []
    unsigned = Payout.query.filter_by(signed=False).count()
    if unsigned:
        attention.append(
            {
                "icon": "cash",
                "text": f"Неподписанных выплат: {unsigned}",
                "url": url_for("payouts.index", signed="0"),
                "css": "danger",
            }
        )

    protocols_no_total = Protocol.query.filter(Protocol.total_amount == 0).count()
    if protocols_no_total:
        attention.append(
            {
                "icon": "file-earmark-text",
                "text": f"Протоколов без суммы: {protocols_no_total}",
                "url": url_for("protocols.index"),
                "css": "warning",
            }
        )

    protocols_no_file = Protocol.query.filter(Protocol.file_path.is_(None)).count()
    if protocols_no_file:
        attention.append(
            {
                "icon": "file-earmark-text",
                "text": f"Протоколов без PDF: {protocols_no_file}",
                "url": url_for("protocols.index"),
                "css": "warning",
            }
        )

    today = date.today()
    jubilee_count = 0
    for m in Member.query.filter(Member.status != "excluded", Member.birth_date.is_not(None)).all():
        nb = m.birth_date.replace(year=today.year)
        if nb < today:
            nb = nb.replace(year=today.year + 1)
        if (nb - today).days <= 30:
            age = nb.year - m.birth_date.year
            if age > 0 and age % 5 == 0:
                jubilee_count += 1
    if jubilee_count:
        attention.append(
            {
                "icon": "cake",
                "text": f"Юбиляров в ближайший месяц: {jubilee_count}",
                "url": url_for("birthdays.index"),
                "css": "info",
            }
        )

    if not FinanceYear.query.filter_by(year=today.year).first():
        attention.append(
            {
                "icon": "cash",
                "text": f"Бюджет на {today.year} год не создан",
                "url": url_for("finances.index"),
                "css": "secondary",
            }
        )

    # данные для офлайн-графиков
    age_buckets = {"до 30": 0, "30-39": 0, "40-49": 0, "50-59": 0, "60+": 0}
    for m in Member.query.filter(Member.status != "excluded", Member.birth_date.is_not(None)).all():
        age = today.year - m.birth_date.year
        if (today.month, today.day) < (m.birth_date.month, m.birth_date.day):
            age -= 1
        if age < 30:
            age_buckets["до 30"] += 1
        elif age < 40:
            age_buckets["30-39"] += 1
        elif age < 50:
            age_buckets["40-49"] += 1
        elif age < 60:
            age_buckets["50-59"] += 1
        else:
            age_buckets["60+"] += 1
    max_age = max(age_buckets.values()) if age_buckets.values() else 1
    age_ranges = [
        {"label": k, "count": v, "percent": int(v / max_age * 100) if max_age else 0}
        for k, v in age_buckets.items()
    ]

    payouts_by_type = (
        db.session.query(PayoutType.name, db.func.count(Payout.id), db.func.sum(Payout.amount))
        .join(Payout, PayoutType.id == Payout.type_id)
        .group_by(PayoutType.name)
        .order_by(db.func.sum(Payout.amount).desc())
        .all()
    )
    max_amount = max((a for _, _, a in payouts_by_type), default=1)
    payouts_chart = [
        {
            "name": name,
            "count": cnt,
            "amount": amount,
            "percent": int(amount / max_amount * 100) if max_amount else 0,
        }
        for name, cnt, amount in payouts_by_type
    ]

    month_counts = dict(
        db.session.query(
            extract("month", Member.entry_date),
            db.func.count(Member.id),
        )
        .filter(
            Member.status != "excluded",
            Member.entry_date.is_not(None),
            extract("year", Member.entry_date) == today.year,
        )
        .group_by(extract("month", Member.entry_date))
        .all()
    )
    member_months = [month_counts.get(i, 0) for i in range(1, 13)]
    max_month = max(member_months) if member_months else 1
    member_months_chart = [
        {"month": MONTH_NAMES[i - 1].title(), "count": c, "percent": int(c / max_month * 100)}
        for i, c in enumerate(member_months, start=1)
    ]

    charts = {
        "age_ranges": age_ranges,
        "payouts_by_type": payouts_chart,
        "member_months": member_months_chart,
    }

    return render_template(
        "dashboard.html",
        total_members=total_members,
        protocols_this_year=protocols_this_year,
        total_payouts=total_payouts,
        members_by_department=members_by_department,
        finance=finance,
        timeline=timeline,
        attention=attention,
        charts=charts,
    )


@bp.route("/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return render_template("search.html", q="", results={})
    like = f"%{q}%"
    members = Member.query.filter(
        Member.full_name.ilike(like)
        | Member.department.ilike(like)
        | Member.position.ilike(like)
    ).all()
    children = MemberChild.query.join(Member).filter(MemberChild.full_name.ilike(like)).all()
    protocols = Protocol.query.filter(Protocol.number.ilike(like)).all()
    payouts = Payout.query.join(Member).filter(Member.full_name.ilike(like)).all()
    return render_template(
        "search.html",
        q=q,
        results={
            "members": members,
            "children": children,
            "protocols": protocols,
            "payouts": payouts,
        },
    )


@bp.route("/timeline")
@login_required
def timeline():
    types = set(request.args.getlist("type")) or {"protocol", "payout", "income"}
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))

    timeline = []
    if "protocol" in types:
        q = Protocol.query.order_by(Protocol.date.desc())
        if date_from:
            q = q.filter(Protocol.date >= date_from)
        if date_to:
            q = q.filter(Protocol.date <= date_to)
        for p in q.limit(100).all():
            timeline.append(
                {
                    "type": "protocol",
                    "date": p.date,
                    "title": f"Протокол №{p.number}",
                    "url": url_for("protocols.detail", id=p.id),
                    "amount": p.total_amount,
                }
            )
    if "payout" in types:
        q = Payout.query.order_by(Payout.date.desc())
        if date_from:
            q = q.filter(Payout.date >= date_from)
        if date_to:
            q = q.filter(Payout.date <= date_to)
        for p in q.limit(100).all():
            timeline.append(
                {
                    "type": "payout",
                    "date": p.date,
                    "title": f"Выплата {p.member.full_name} ({p.type.name})",
                    "url": url_for("payouts.index"),
                    "amount": p.amount,
                }
            )
    if "income" in types:
        q = FinanceMonth.query.order_by(FinanceMonth.date_received.desc())
        if date_from:
            q = q.filter(FinanceMonth.date_received >= date_from)
        if date_to:
            q = q.filter(FinanceMonth.date_received <= date_to)
        for fm in q.limit(100).all():
            timeline.append(
                {
                    "type": "income",
                    "date": fm.date_received or date(fm.year.year, fm.month, 1),
                    "title": f"Приход за {fm.month}.{fm.year.year}",
                    "url": url_for("finances.index", year_id=fm.year_id),
                    "amount": fm.gross_amount,
                }
            )
    timeline.sort(key=lambda x: x["date"], reverse=True)
    timeline = timeline[:100]
    return render_template(
        "timeline.html",
        timeline=timeline,
        types=types,
        date_from=date_from,
        date_to=date_to,
    )
