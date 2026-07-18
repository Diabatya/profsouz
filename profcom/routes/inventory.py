from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import InventoryItem, Member, db
from utils import apply_sort, login_required, parse_date, parse_decimal

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@bp.route("/")
@login_required
def index():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "inventory_number")
    order = request.args.get("order", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    q = InventoryItem.query
    if search:
        q = q.filter(
            (InventoryItem.name.ilike(f"%{search}%"))
            | (InventoryItem.inventory_number.ilike(f"%{search}%"))
        )
    if status:
        q = q.filter(InventoryItem.status == status)

    q = apply_sort(q, sort, order, InventoryItem, ["inventory_number", "name", "acquisition_date"])
    pagination = q.paginate(page=page, per_page=max(per_page, 5), error_out=False)
    return render_template(
        "inventory/list.html",
        items=pagination.items,
        pagination=pagination,
        search=search,
        status=status,
        sort=sort,
        order=order,
        per_page=per_page,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    if request.method == "POST":
        inventory_number = (request.form.get("inventory_number") or "").strip()
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        quantity = parse_decimal(request.form.get("quantity", "1"))
        unit = (request.form.get("unit") or "").strip() or "шт."
        acquisition_date = parse_date(request.form.get("acquisition_date"))
        storage_term_years = request.form.get("storage_term_years", type=int) or 0
        location = (request.form.get("location") or "").strip() or None
        responsible_member_id = request.form.get("responsible_member_id", type=int) or None

        if not inventory_number or not name:
            flash("Укажите инвентарный номер и наименование", "danger")
            return render_template("inventory/add.html", members=members)

        item = InventoryItem(
            inventory_number=inventory_number,
            name=name,
            description=description,
            quantity=quantity,
            unit=unit,
            acquisition_date=acquisition_date,
            storage_term_years=storage_term_years,
            location=location,
            responsible_member_id=responsible_member_id,
        )
        db.session.add(item)
        db.session.commit()
        flash("Ценность добавлена", "success")
        return redirect(url_for("inventory.index"))
    return render_template("inventory/add.html", members=members)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    item = db.session.get(InventoryItem, id) or abort(404)
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    if request.method == "POST":
        item.inventory_number = (request.form.get("inventory_number") or "").strip()
        item.name = (request.form.get("name") or "").strip()
        item.description = (request.form.get("description") or "").strip() or None
        item.quantity = parse_decimal(request.form.get("quantity", "1"))
        item.unit = (request.form.get("unit") or "").strip() or "шт."
        item.acquisition_date = parse_date(request.form.get("acquisition_date"))
        item.storage_term_years = request.form.get("storage_term_years", type=int) or 0
        item.location = (request.form.get("location") or "").strip() or None
        item.responsible_member_id = request.form.get("responsible_member_id", type=int) or None
        item.status = request.form.get("status", "active")

        if not item.inventory_number or not item.name:
            flash("Укажите инвентарный номер и наименование", "danger")
            return render_template("inventory/edit.html", item=item, members=members)

        db.session.commit()
        flash("Ценность обновлена", "success")
        return redirect(url_for("inventory.index"))
    return render_template("inventory/edit.html", item=item, members=members)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    item = db.session.get(InventoryItem, id) or abort(404)
    db.session.delete(item)
    db.session.commit()
    flash("Ценность удалена", "success")
    return redirect(url_for("inventory.index"))


@bp.route("/export")
@login_required
def export():
    from utils import excel_response

    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    q = InventoryItem.query
    if search:
        q = q.filter(
            (InventoryItem.name.ilike(f"%{search}%"))
            | (InventoryItem.inventory_number.ilike(f"%{search}%"))
        )
    if status:
        q = q.filter(InventoryItem.status == status)

    rows = []
    for item in q.order_by(InventoryItem.inventory_number).all():
        responsible = item.responsible.full_name if item.responsible else "-"
        storage_until = item.storage_until.strftime("%d.%m.%Y") if item.storage_until else "-"
        rows.append(
            [
                item.inventory_number,
                item.name,
                item.description or "-",
                float(item.quantity),
                item.unit,
                item.acquisition_date.strftime("%d.%m.%Y") if item.acquisition_date else "-",
                storage_until,
                item.location or "-",
                item.status,
                responsible,
            ]
        )
    headers = [
        "Инв. номер",
        "Наименование",
        "Описание",
        "Кол-во",
        "Ед.",
        "Дата поступления",
        "Срок хранения",
        "Место",
        "Статус",
        "Ответственный",
    ]
    return excel_response(headers, rows, "inventory.xlsx")
