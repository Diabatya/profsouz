from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from models import Member, Payout, PayoutType, Protocol, db
from utils import apply_sort, login_required, parse_date, parse_decimal, period_bounds

bp = Blueprint("payouts", __name__, url_prefix="/payouts")


@bp.route("/")
@login_required
def index():
    q = Payout.query.join(Member).join(PayoutType)
    ptype = request.args.get("type", "")
    signed = request.args.get("signed", "")
    period = request.args.get("period", "")
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if period:
        date_from, date_to = period_bounds(period)
    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if ptype:
        q = q.filter(Payout.type_id == int(ptype))
    if signed:
        q = q.filter(Payout.signed == (signed == "1"))
    if date_from:
        q = q.filter(Payout.date >= date_from)
    if date_to:
        q = q.filter(Payout.date <= date_to)

    q = apply_sort(q, sort, order, Payout, ["date", "amount"])
    pagination = q.paginate(page=page, per_page=max(per_page, 5), error_out=False)
    types = PayoutType.query.order_by(PayoutType.name).all()
    total = db.session.query(func.sum(Payout.amount)).scalar() or 0
    filtered_total = q.with_entities(func.sum(Payout.amount)).scalar() or 0
    return render_template(
        "payouts/list.html",
        payouts=pagination.items,
        pagination=pagination,
        types=types,
        selected_type=ptype,
        selected_signed=signed,
        period=period,
        date_from=request.args.get("date_from", ""),
        date_to=request.args.get("date_to", ""),
        total=total,
        filtered_total=filtered_total,
        sort=sort,
        order=order,
        per_page=per_page,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    pre_member_id = request.args.get("member_id", type=int)
    pre_amount = request.args.get("amount")
    types = PayoutType.query.order_by(PayoutType.name).all()
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    protocols = Protocol.query.order_by(Protocol.date.desc()).all()

    if request.method == "POST":
        member_id = request.form.get("member_id", type=int)
        type_id = request.form.get("type_id", type=int)
        protocol_id = request.form.get("protocol_id") or None
        protocol_id = int(protocol_id) if protocol_id else None
        amount = parse_decimal(request.form.get("amount", "0"))
        pdate = parse_date(request.form.get("date"))
        signed = bool(request.form.get("signed"))

        member = db.session.get(Member, member_id) if member_id else None
        ptype = db.session.get(PayoutType, type_id) if type_id else None

        if not member or not ptype or not pdate:
            flash("Заполните все обязательные поля", "danger")
            return render_template(
                "payouts/add.html",
                types=types,
                members=members,
                protocols=protocols,
                pre_member_id=member_id or pre_member_id,
                pre_amount=pre_amount,
                pre_type=type_id,
            )
        if not member.is_active:
            flash("Выплаты возможны только активным членам", "danger")
            return render_template(
                "payouts/add.html",
                types=types,
                members=members,
                protocols=protocols,
                pre_member_id=member_id,
                pre_amount=pre_amount,
                pre_type=type_id,
            )

        payout = Payout(
            member_id=member.id,
            type_id=ptype.id,
            protocol_id=protocol_id,
            amount=amount,
            date=pdate,
            signed=signed,
        )
        db.session.add(payout)
        db.session.commit()
        flash("Выплата добавлена", "success")
        return redirect(url_for("payouts.index"))

    return render_template(
        "payouts/add.html",
        types=types,
        members=members,
        protocols=protocols,
        pre_member_id=pre_member_id,
        pre_amount=pre_amount,
        pre_type=None,
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    payout = db.session.get(Payout, id) or abort(404)
    types = PayoutType.query.order_by(PayoutType.name).all()
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    protocols = Protocol.query.order_by(Protocol.date.desc()).all()

    if request.method == "POST":
        type_id = request.form.get("type_id", type=int)
        protocol_id = request.form.get("protocol_id") or None
        protocol_id = int(protocol_id) if protocol_id else None
        amount = parse_decimal(request.form.get("amount", "0"))
        pdate = parse_date(request.form.get("date"))
        signed = bool(request.form.get("signed"))

        ptype = db.session.get(PayoutType, type_id) if type_id else None
        if not ptype or not pdate:
            flash("Заполните обязательные поля", "danger")
            return render_template(
                "payouts/edit.html",
                payout=payout,
                types=types,
                members=members,
                protocols=protocols,
            )

        payout.type_id = ptype.id
        payout.protocol_id = protocol_id
        payout.amount = amount
        payout.date = pdate
        payout.signed = signed
        db.session.commit()
        flash("Выплата обновлена", "success")
        return redirect(url_for("payouts.index"))

    return render_template(
        "payouts/edit.html", payout=payout, types=types, members=members, protocols=protocols
    )


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    payout = db.session.get(Payout, id) or abort(404)
    db.session.delete(payout)
    db.session.commit()
    flash("Выплата удалена", "success")
    return redirect(url_for("payouts.index"))


@bp.route("/export")
@login_required
def export():
    from utils import excel_response

    q = Payout.query.join(Member).join(PayoutType)
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if date_from:
        q = q.filter(Payout.date >= date_from)
    if date_to:
        q = q.filter(Payout.date <= date_to)

    payouts = q.order_by(Payout.date.desc()).all()
    headers = ["Дата", "Член", "Тип выплаты", "Протокол", "Сумма", "Подписана"]
    rows = []
    for p in payouts:
        protocol = p.protocol.number if p.protocol else ""
        rows.append(
            [
                p.date.strftime("%d.%m.%Y"),
                p.member.full_name,
                p.type.name,
                protocol,
                float(p.amount),
                "Да" if p.signed else "Нет",
            ]
        )
    return excel_response(headers, rows, "viplaty.xlsx")
