from datetime import date

from flask import Blueprint, render_template, request
from sqlalchemy import extract

from models import AnniversarySetting, Member
from utils import login_required

bp = Blueprint("birthdays", __name__, url_prefix="/birthdays")


ANNIVERSARY_AGES = {20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70}


@bp.route("/")
@login_required
def index():
    today = date.today()
    month = request.args.get("month", type=int) or today.month
    members = (
        Member.query.filter(extract("month", Member.birth_date) == month)
        .order_by(extract("day", Member.birth_date))
        .all()
    )

    settings = {s.age: float(s.amount) for s in AnniversarySetting.query.all()}
    rows = []
    for m in members:
        age_to_turn = today.year - m.birth_date.year
        is_anniversary = age_to_turn in ANNIVERSARY_AGES
        amount = settings.get(age_to_turn, 0)
        rows.append(
            {
                "member": m,
                "age": age_to_turn,
                "is_anniversary": is_anniversary,
                "amount": amount,
            }
        )

    return render_template(
        "birthdays.html",
        rows=rows,
        month=month,
        months=list(range(1, 13)),
        today=today,
        anniversary_ages=ANNIVERSARY_AGES,
    )
