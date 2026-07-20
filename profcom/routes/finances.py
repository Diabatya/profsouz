from collections import defaultdict
from decimal import Decimal

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from models import FinanceDistributionRule, FinanceRecord, FinanceRecordDistribution, db
from utils import (
    apply_sort,
    dictionary_values,
    login_required,
    parse_date,
    parse_decimal,
    period_bounds,
    save_dictionary_value,
)

bp = Blueprint("finances", __name__, url_prefix="/finances")


def _apply_distribution(record):
    """Удаляет старые распределения и рассчитывает новые для дохода."""
    if record.type != "income":
        return
    FinanceRecordDistribution.query.filter_by(record_id=record.id).delete()
    rules = (
        FinanceDistributionRule.query.filter_by(active=True)
        .order_by(FinanceDistributionRule.order, FinanceDistributionRule.name)
        .all()
    )
    primary = next((r for r in rules if r.is_primary), None)
    commission_total = Decimal(0)
    amounts = {}
    for rule in rules:
        amount = (record.amount * rule.percent) / Decimal(100)
        if rule.is_bank_commission:
            commission_total += amount
        amounts[rule.id] = amount

    if primary and primary.id in amounts:
        primary_amount = amounts[primary.id] - commission_total
        if primary_amount < 0:
            primary_amount = Decimal(0)
        amounts[primary.id] = primary_amount

    for rule in rules:
        amount = amounts[rule.id]
        if amount > 0:
            db.session.add(
                FinanceRecordDistribution(
                    record_id=record.id,
                    rule_id=rule.id,
                    name=rule.name,
                    amount=amount,
                )
            )


def _active_funds():
    return (
        FinanceDistributionRule.query.filter_by(active=True)
        .order_by(FinanceDistributionRule.order, FinanceDistributionRule.name)
        .all()
    )


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
    funds = _active_funds()
    primary = next((f for f in funds if f.is_primary), funds[0] if funds else None)
    primary_fund_id = primary.id if primary else None

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount = parse_decimal(request.form.get("amount", "0"))
        rdate = parse_date(request.form.get("date"))
        rtype = request.form.get("type", "")
        category = request.form.get("category", "").strip() or "прочее"
        fund_id = request.form.get("fund_id", type=int) or primary_fund_id

        if not description or not rdate or not rtype:
            flash("Заполните все обязательные поля", "danger")
            return render_template(
                "finances/add.html",
                descriptions=dictionary_values("finance_description"),
                categories=dictionary_values("finance_category"),
                funds=funds,
                primary_fund_id=primary_fund_id,
            )

        if rtype == "expense" and not fund_id:
            flash("Выберите фонд для расхода", "danger")
            return render_template(
                "finances/add.html",
                descriptions=dictionary_values("finance_description"),
                categories=dictionary_values("finance_category"),
                funds=funds,
                primary_fund_id=primary_fund_id,
            )

        description = save_dictionary_value("finance_description", description) or description
        category = save_dictionary_value("finance_category", category) or category
        record = FinanceRecord(
            description=description,
            amount=amount,
            date=rdate,
            type=rtype,
            category=category,
            fund_id=fund_id if rtype == "expense" else None,
        )
        db.session.add(record)
        db.session.flush()
        _apply_distribution(record)
        db.session.commit()
        flash("Запись добавлена", "success")
        return redirect(url_for("finances.index"))
    return render_template(
        "finances/add.html",
        descriptions=dictionary_values("finance_description"),
        categories=dictionary_values("finance_category"),
        funds=funds,
        primary_fund_id=primary_fund_id,
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    record = db.session.get(FinanceRecord, id) or abort(404)
    funds = _active_funds()
    primary = next((f for f in funds if f.is_primary), funds[0] if funds else None)
    primary_fund_id = primary.id if primary else None
    selected_fund_id = record.fund_id or primary_fund_id

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount = parse_decimal(request.form.get("amount", "0"))
        rdate = parse_date(request.form.get("date"))
        rtype = request.form.get("type", "")
        category = request.form.get("category", "").strip() or "прочее"
        fund_id = request.form.get("fund_id", type=int) or primary_fund_id

        if not description or not rdate or not rtype:
            flash("Заполните все обязательные поля", "danger")
            return render_template(
                "finances/edit.html",
                record=record,
                descriptions=dictionary_values("finance_description"),
                categories=dictionary_values("finance_category"),
                funds=funds,
                primary_fund_id=primary_fund_id,
            )

        if rtype == "expense" and not fund_id:
            flash("Выберите фонд для расхода", "danger")
            return render_template(
                "finances/edit.html",
                record=record,
                descriptions=dictionary_values("finance_description"),
                categories=dictionary_values("finance_category"),
                funds=funds,
                primary_fund_id=primary_fund_id,
            )

        record.description = (
            save_dictionary_value("finance_description", description) or description
        )
        record.amount = amount
        record.date = rdate
        record.type = rtype
        record.category = save_dictionary_value("finance_category", category) or category
        record.fund_id = fund_id if rtype == "expense" else None
        _apply_distribution(record)
        db.session.commit()
        flash("Запись обновлена", "success")
        return redirect(url_for("finances.index"))
    return render_template(
        "finances/edit.html",
        record=record,
        descriptions=dictionary_values("finance_description"),
        categories=dictionary_values("finance_category"),
        funds=funds,
        primary_fund_id=primary_fund_id,
        selected_fund_id=selected_fund_id,
    )


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


@bp.route("/report")
@login_required
def report():
    period = request.args.get("period", "")
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if period:
        date_from, date_to = period_bounds(period)

    q = FinanceRecord.query
    if date_from:
        q = q.filter(FinanceRecord.date >= date_from)
    if date_to:
        q = q.filter(FinanceRecord.date <= date_to)

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

    distribution_q = db.session.query(
        FinanceRecordDistribution.name,
        func.sum(FinanceRecordDistribution.amount).label("total"),
    ).join(FinanceRecord)
    if date_from:
        distribution_q = distribution_q.filter(FinanceRecord.date >= date_from)
    if date_to:
        distribution_q = distribution_q.filter(FinanceRecord.date <= date_to)
    distributions = (
        distribution_q.group_by(FinanceRecordDistribution.name)
        .order_by(func.sum(FinanceRecordDistribution.amount).desc())
        .all()
    )

    category_q = db.session.query(
        FinanceRecord.type,
        FinanceRecord.category,
        func.sum(FinanceRecord.amount).label("total"),
    )
    if date_from:
        category_q = category_q.filter(FinanceRecord.date >= date_from)
    if date_to:
        category_q = category_q.filter(FinanceRecord.date <= date_to)
    categories = (
        category_q.group_by(FinanceRecord.type, FinanceRecord.category)
        .order_by(func.sum(FinanceRecord.amount).desc())
        .all()
    )

    total_distributed = sum(d.total for d in distributions) if distributions else 0
    balance = income - expense
    net = balance - total_distributed

    active_funds = (
        FinanceDistributionRule.query.filter_by(active=True)
        .order_by(FinanceDistributionRule.order, FinanceDistributionRule.name)
        .all()
    )
    active_names = [f.name for f in active_funds]

    monthly_q = (
        db.session.query(
            func.strftime("%Y-%m", FinanceRecord.date).label("month"),
            FinanceRecordDistribution.name,
            func.sum(FinanceRecordDistribution.amount).label("total"),
        )
        .join(FinanceRecord)
        .filter(FinanceRecord.type == "income")
    )
    if date_from:
        monthly_q = monthly_q.filter(FinanceRecord.date >= date_from)
    if date_to:
        monthly_q = monthly_q.filter(FinanceRecord.date <= date_to)
    monthly_rows = (
        monthly_q.group_by("month", FinanceRecordDistribution.name)
        .order_by("month")
        .all()
    )

    income_monthly_q = (
        db.session.query(
            func.strftime("%Y-%m", FinanceRecord.date).label("month"),
            func.sum(FinanceRecord.amount).label("total"),
        )
        .filter(FinanceRecord.type == "income")
    )
    if date_from:
        income_monthly_q = income_monthly_q.filter(FinanceRecord.date >= date_from)
    if date_to:
        income_monthly_q = income_monthly_q.filter(FinanceRecord.date <= date_to)
    income_by_month = {
        r.month: r.total
        for r in income_monthly_q.group_by("month").order_by("month").all()
    }

    month_funds = defaultdict(lambda: defaultdict(lambda: Decimal(0)))
    fund_totals = defaultdict(lambda: Decimal(0))
    all_names = set(active_names)
    for r in monthly_rows:
        month_funds[r.month][r.name] = r.total
        fund_totals[r.name] += r.total
        all_names.add(r.name)

    fund_names = [n for n in active_names if n in all_names]
    fund_names.extend(sorted(all_names - set(active_names)))

    month_rows = []
    for m in sorted(set(income_by_month.keys()) | set(month_funds.keys())):
        month_rows.append(
            {
                "month": m,
                "label": f"{m[5:7]}.{m[:4]}",
                "income": income_by_month.get(m, Decimal(0)),
                "funds": {name: month_funds[m].get(name, Decimal(0)) for name in fund_names},
            }
        )

    expense_q = (
        db.session.query(
            FinanceDistributionRule.name,
            func.sum(FinanceRecord.amount).label("total"),
        )
        .join(FinanceRecord, FinanceDistributionRule.id == FinanceRecord.fund_id)
        .filter(FinanceRecord.type == "expense")
    )
    if date_from:
        expense_q = expense_q.filter(FinanceRecord.date >= date_from)
    if date_to:
        expense_q = expense_q.filter(FinanceRecord.date <= date_to)
    expenses_by_fund = {r.name: r.total for r in expense_q.group_by(FinanceDistributionRule.name).all()}

    fund_balances = []
    for name in fund_names:
        in_amt = fund_totals.get(name, Decimal(0))
        out_amt = expenses_by_fund.get(name, Decimal(0)) or Decimal(0)
        fund_balances.append(
            {
                "name": name,
                "in": in_amt,
                "out": out_amt,
                "balance": in_amt - out_amt,
            }
        )

    return render_template(
        "finances/report.html",
        income=income,
        expense=expense,
        balance=balance,
        net=net,
        total_distributed=total_distributed,
        distributions=distributions,
        categories=categories,
        fund_names=fund_names,
        month_rows=month_rows,
        fund_totals=fund_totals,
        fund_balances=fund_balances,
        period=period,
        date_from=request.args.get("date_from", ""),
        date_to=request.args.get("date_to", ""),
    )
