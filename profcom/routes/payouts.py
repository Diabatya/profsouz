from datetime import date

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func

from models import (
    Member,
    MemberChild,
    Payout,
    PayoutCategory,
    PayoutType,
    Protocol,
    db,
)
from utils import (
    apply_sort,
    excel_response,
    login_required,
    parse_date,
    parse_decimal,
    period_bounds,
)

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


def _categories_data():
    return [
        {"id": c.id, "type_id": c.payout_type_id, "name": c.name, "amount": float(c.amount)}
        for c in PayoutCategory.query.order_by(PayoutCategory.name).all()
    ]


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    pre_member_id = request.args.get("member_id", type=int)
    pre_amount = request.args.get("amount")
    types = PayoutType.query.order_by(PayoutType.name).all()
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    protocols = Protocol.query.order_by(Protocol.date.desc()).all()
    categories = _categories_data()

    if request.method == "POST":
        member_id = request.form.get("member_id", type=int)
        type_id = request.form.get("type_id", type=int)
        category_id = request.form.get("category_id") or None
        category_id = int(category_id) if category_id else None
        protocol_id = request.form.get("protocol_id") or None
        protocol_id = int(protocol_id) if protocol_id else None
        pdate = parse_date(request.form.get("date"))
        signed = bool(request.form.get("signed"))
        note = (request.form.get("note") or "").strip()

        member = db.session.get(Member, member_id) if member_id else None
        ptype = db.session.get(PayoutType, type_id) if type_id else None
        category = db.session.get(PayoutCategory, category_id) if category_id else None

        amount = parse_decimal(request.form.get("amount", "0"))
        if not request.form.get("amount") and category:
            amount = category.amount
        elif not request.form.get("amount") and ptype:
            amount = ptype.default_amount

        if not member or not ptype or not pdate:
            flash("Заполните все обязательные поля", "danger")
            return render_template(
                "payouts/add.html",
                types=types,
                members=members,
                protocols=protocols,
                categories=categories,
                pre_member_id=member_id or pre_member_id,
                pre_amount=pre_amount,
                pre_type=type_id,
                pre_category=category_id,
            )
        if not member.is_active:
            flash("Выплаты возможны только активным членам", "danger")
            return render_template(
                "payouts/add.html",
                types=types,
                members=members,
                protocols=protocols,
                categories=categories,
                pre_member_id=member_id,
                pre_amount=pre_amount,
                pre_type=type_id,
                pre_category=category_id,
            )

        payout = Payout(
            member_id=member.id,
            type_id=ptype.id,
            category_id=category.id if category else None,
            protocol_id=protocol_id,
            amount=amount,
            date=pdate,
            signed=signed,
            note=note,
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
        categories=categories,
        pre_member_id=pre_member_id,
        pre_amount=pre_amount,
        pre_type=None,
        pre_category=None,
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    payout = db.session.get(Payout, id) or abort(404)
    types = PayoutType.query.order_by(PayoutType.name).all()
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    protocols = Protocol.query.order_by(Protocol.date.desc()).all()

    categories = _categories_data()

    if request.method == "POST":
        type_id = request.form.get("type_id", type=int)
        category_id = request.form.get("category_id") or None
        category_id = int(category_id) if category_id else None
        protocol_id = request.form.get("protocol_id") or None
        protocol_id = int(protocol_id) if protocol_id else None
        pdate = parse_date(request.form.get("date"))
        signed = bool(request.form.get("signed"))
        note = (request.form.get("note") or "").strip()

        ptype = db.session.get(PayoutType, type_id) if type_id else None
        category = db.session.get(PayoutCategory, category_id) if category_id else None

        amount = parse_decimal(request.form.get("amount", "0"))
        if not request.form.get("amount") and category:
            amount = category.amount
        elif not request.form.get("amount") and ptype:
            amount = ptype.default_amount

        if not ptype or not pdate:
            flash("Заполните обязательные поля", "danger")
            return render_template(
                "payouts/edit.html",
                payout=payout,
                types=types,
                members=members,
                protocols=protocols,
                categories=categories,
            )

        payout.type_id = ptype.id
        payout.category_id = category.id if category else None
        payout.protocol_id = protocol_id
        payout.amount = amount
        payout.date = pdate
        payout.signed = signed
        payout.note = note
        db.session.commit()
        flash("Выплата обновлена", "success")
        return redirect(url_for("payouts.index"))

    return render_template(
        "payouts/edit.html",
        payout=payout,
        types=types,
        members=members,
        protocols=protocols,
        categories=categories,
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
    q = Payout.query.join(Member).join(PayoutType)
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if date_from:
        q = q.filter(Payout.date >= date_from)
    if date_to:
        q = q.filter(Payout.date <= date_to)

    payouts = q.order_by(Payout.date.desc()).all()
    headers = ["Дата", "Член", "Тип выплаты", "Категория", "Протокол", "Сумма", "Подписана"]
    rows = []
    for p in payouts:
        protocol = p.protocol.number if p.protocol else ""
        rows.append(
            [
                p.date.strftime("%d.%m.%Y"),
                p.member.full_name,
                p.type.name,
                p.category.name if p.category else "",
                protocol,
                float(p.amount),
                "Да" if p.signed else "Нет",
            ]
        )
    return excel_response(headers, rows, "viplaty.xlsx")


def _child_age(child, today):
    if not child.birth_date:
        return None
    age = today.year - child.birth_date.year
    if (today.month, today.day) < (child.birth_date.month, child.birth_date.day):
        age -= 1
    return age


@bp.route("/gifts", methods=["GET", "POST"])
@login_required
def gifts():
    gift_type = PayoutType.query.filter_by(name="Подарок").first()
    if not gift_type:
        flash("В настройках отсутствует тип выплаты 'Подарок'", "danger")
        return redirect(url_for("payouts.index"))

    today = date.today()
    age_from = request.args.get("age_from", type=int)
    age_to = request.args.get("age_to", type=int)
    member_id = request.args.get("member_id", type=int)

    q = MemberChild.query.join(Member).order_by(Member.full_name, MemberChild.full_name)
    if member_id:
        q = q.filter(MemberChild.member_id == member_id)
    children = q.all()

    rows = []
    for child in children:
        age = _child_age(child, today)
        if age_from is not None and (age is None or age < age_from):
            continue
        if age_to is not None and (age is None or age > age_to):
            continue
        rows.append({"child": child, "age": age})

    if request.method == "POST":
        selected = request.form.getlist("child_id", type=int)
        amount = parse_decimal(request.form.get("amount", "0"))
        pdate = parse_date(request.form.get("date"))
        note = (request.form.get("note") or "").strip()
        if not selected:
            flash("Выберите хотя бы одного ребенка", "danger")
        elif not pdate or not amount:
            flash("Укажите сумму и дату", "danger")
        else:
            count = 0
            for child_id in selected:
                child = db.session.get(MemberChild, child_id)
                if not child:
                    continue
                payout = Payout(
                    member_id=child.member_id,
                    child_id=child.id,
                    type_id=gift_type.id,
                    amount=amount,
                    date=pdate,
                    note=note,
                )
                db.session.add(payout)
                count += 1
            db.session.commit()
            flash(f"Создано {count} выплат", "success")
            return redirect(
                url_for("payouts.gifts", age_from=age_from, age_to=age_to, member_id=member_id)
            )

    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    return render_template(
        "payouts/gifts.html",
        rows=rows,
        members=members,
        age_from=age_from,
        age_to=age_to,
        member_id=member_id,
        gift_type=gift_type,
    )


@bp.route("/gifts/export")
@login_required
def gift_export():
    gift_type = PayoutType.query.filter_by(name="Подарок").first()
    if not gift_type:
        flash("В настройках отсутствует тип выплаты 'Подарок'", "danger")
        return redirect(url_for("payouts.index"))
    q = Payout.query.join(Member).join(MemberChild).filter(Payout.type_id == gift_type.id)
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if date_from:
        q = q.filter(Payout.date >= date_from)
    if date_to:
        q = q.filter(Payout.date <= date_to)
    payouts = q.order_by(Payout.date.desc()).all()
    headers = ["Дата", "Член", "Ребенок", "Сумма", "Примечание", "Подписана"]
    rows = []
    for p in payouts:
        child_name = p.child.full_name if p.child else ""
        rows.append(
            [
                p.date.strftime("%d.%m.%Y"),
                p.member.full_name,
                child_name,
                float(p.amount),
                p.note or "",
                "Да" if p.signed else "Нет",
            ]
        )
    return excel_response(headers, rows, "podarki.xlsx")
