from datetime import date, datetime

from flask import Blueprint, current_app, render_template, request, send_from_directory, url_for
from sqlalchemy import func

from models import Group, Member, MemberStatusHistory, Payout, Protocol, db
from utils import login_required

bp = Blueprint("main", __name__)


def birthday_in_year(birth_date, year):
    try:
        return birth_date.replace(year=year)
    except ValueError:
        return date(year, birth_date.month, birth_date.day - 1)


@bp.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    total_members = Member.query.filter_by(status="active").count()
    protocols_count = Protocol.query.filter(func.strftime("%Y", Protocol.date) == str(today.year)).count()
    total_payouts = db.session.query(func.sum(Payout.amount)).scalar() or 0

    department_stats = (
        db.session.query(Member.department, func.count(Member.id).label("cnt"))
        .filter_by(status="active")
        .group_by(Member.department)
        .order_by(func.count(Member.id).desc())
        .all()
    )

    recent_members = Member.query.order_by(Member.id.desc()).limit(5).all()
    recent_payouts = Payout.query.order_by(Payout.id.desc()).limit(5).all()

    upcoming = []
    active_members = Member.query.filter_by(status="active").all()
    for m in active_members:
        bday = birthday_in_year(m.birth_date, today.year)
        if bday < today:
            bday = birthday_in_year(m.birth_date, today.year + 1)
        days = (bday - today).days
        if days <= 30:
            upcoming.append(
                {
                    "member": m,
                    "date": bday,
                    "age": bday.year - m.birth_date.year,
                    "days": days,
                }
            )
    upcoming.sort(key=lambda x: x["days"])

    return render_template(
        "dashboard.html",
        total_members=total_members,
        protocols_count=protocols_count,
        total_payouts=total_payouts,
        department_stats=department_stats,
        recent_members=recent_members,
        recent_payouts=recent_payouts,
        upcoming_birthdays=upcoming,
    )


@bp.route("/public/profkom")
def public_profkom():
    gender = request.args.get("gender", "")
    groups = Group.query.filter_by(type="profkom").order_by(Group.name).all()
    rank = {"Председатель": 0, "Заместитель председателя": 1, "Секретарь": 2, "Член профкома": 3}
    members_by_group = {}
    for g in groups:
        members = [m for m in g.members if m.status == "active"]
        if gender in ("male", "female"):
            members = [m for m in members if m.gender_or_detect == gender]
        members_by_group[g.id] = sorted(
            members, key=lambda m: rank.get(m.position or "Член профкома", 99)
        )
    return render_template(
        "public/profkom.html",
        groups=groups,
        members_by_group=members_by_group,
        selected_gender=gender,
    )


@bp.route("/timeline")
@login_required
def timeline():
    items = []
    for h in (
        MemberStatusHistory.query.order_by(MemberStatusHistory.changed_at.desc()).limit(50).all()
    ):
        items.append(
            {
                "time": h.changed_at,
                "icon": "person" if h.new_status == "active" else "person-x",
                "color": "success" if h.new_status == "active" else "secondary",
                "text": f"{h.member.full_name}: {h.note or h.new_status}",
                "link": url_for("members.detail", id=h.member_id),
            }
        )
    for p in Payout.query.order_by(Payout.date.desc()).limit(20).all():
        items.append(
            {
                "time": datetime.combine(p.date, datetime.min.time()),
                "icon": "cash",
                "color": "primary",
                "text": f"Выплата {float(p.amount)} ₽ — {p.member.full_name}",
                "link": url_for("payouts.index"),
            }
        )
    items.sort(key=lambda x: x["time"], reverse=True)
    return render_template("timeline.html", items=items[:50])


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
