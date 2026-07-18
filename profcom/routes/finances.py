from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from models import FinanceRecord, db
from utils import apply_sort, login_required, parse_date, parse_decimal, period_bounds

bp = Blueprint("finances", __name__, url_prefix="/finances")


@bp.route("/")
@login_required
def index():
    q = FinanceRecord.query
    period = request.args.get("period", "")
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if period:
        date_from, date_to = period_bounds(period)
    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if date_from:
        q = q.filter(FinanceRecord.date >= date_from)
    if date_to:
        q = q.filter(FinanceRecord.date <= date_to)

    q = apply_sort(q, sort, order, FinanceRecord, ["date", "amount"])
    pagination = q.paginate(page=page, per_page=max(per_page, 5), error_out=False)
    income = (
        q.filter(FinanceRecord.type == "income")
        .with_entities(func.sum(FinanceRecord.amount))
        .scalar()
        or 0
    )
    expense = (
        q.filter(FinanceRecord.type == "expense")
        .with_entities(func.sum(FinanceRecord.amount))
        .scalar()
        or 0
    )
    balance = income - expense
    return render_template(
        "finances/list.html",
        records=pagination.items,
        pagination=pagination,
        income=income,
        expense=expense,
        balance=balance,
        period=period,
        date_from=request.args.get("date_from", ""),
        date_to=request.args.get("date_to", ""),
        sort=sort,
        order=order,
        per_page=per_page,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount = parse_decimal(request.form.get("amount", "0"))
        rdate = parse_date(request.form.get("date"))
        rtype = request.form.get("type", "")
        category = request.form.get("category", "").strip() or "прочее"

        if not description or not rdate or not rtype:
            flash("Заполните все обязательные поля", "danger")
            return render_template("finances/add.html")

        record = FinanceRecord(
            description=description, amount=amount, date=rdate, type=rtype, category=category
        )
        db.session.add(record)
        db.session.commit()
        flash("Запись добавлена", "success")
        return redirect(url_for("finances.index"))
    return render_template("finances/add.html")


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    record = db.session.get(FinanceRecord, id) or abort(404)
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount = parse_decimal(request.form.get("amount", "0"))
        rdate = parse_date(request.form.get("date"))
        rtype = request.form.get("type", "")
        category = request.form.get("category", "").strip() or "прочее"

        if not description or not rdate or not rtype:
            flash("Заполните все обязательные поля", "danger")
            return render_template("finances/edit.html", record=record)

        record.description = description
        record.amount = amount
        record.date = rdate
        record.type = rtype
        record.category = category
        db.session.commit()
        flash("Запись обновлена", "success")
        return redirect(url_for("finances.index"))
    return render_template("finances/edit.html", record=record)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    record = db.session.get(FinanceRecord, id) or abort(404)
    db.session.delete(record)
    db.session.commit()
    flash("Запись удалена", "success")
    return redirect(url_for("finances.index"))


@bp.route("/export")
@login_required
def export():
    from utils import excel_response

    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    q = FinanceRecord.query
    if date_from:
        q = q.filter(FinanceRecord.date >= date_from)
    if date_to:
        q = q.filter(FinanceRecord.date <= date_to)

    rows = []
    for r in q.order_by(FinanceRecord.date.desc()).all():
        rows.append(
            [r.date.strftime("%d.%m.%Y"), r.description, r.type, r.category, float(r.amount)]
        )
    headers = ["Дата", "Описание", "Тип", "Категория", "Сумма"]
    return excel_response(headers, rows, "finansi.xlsx")
