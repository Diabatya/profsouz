import os
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from models import Payout, Protocol, db
from utils import apply_sort, login_required, parse_date, parse_decimal

bp = Blueprint("protocols", __name__, url_prefix="/protocols")


def allowed_pdf(filename):
    return filename and filename.lower().endswith(".pdf")


@bp.route("/")
@login_required
def index():
    q = Protocol.query
    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    q = apply_sort(q, sort, order, Protocol, ["date", "number", "total_amount"])
    pagination = q.paginate(page=page, per_page=max(per_page, 5), error_out=False)
    return render_template(
        "protocols/list.html",
        protocols=pagination.items,
        pagination=pagination,
        sort=sort,
        order=order,
        per_page=per_page,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        number = request.form.get("number", "").strip()
        pdate = parse_date(request.form.get("date"))
        total = parse_decimal(request.form.get("total_amount", "0"))
        file = request.files.get("file")

        if not number or not pdate:
            flash("Укажите номер и дату протокола", "danger")
            return render_template("protocols/add.html")

        file_path = None
        if file and allowed_pdf(file.filename):
            filename = f"{uuid4()}.pdf"
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

        protocol = Protocol(number=number, date=pdate, total_amount=total, file_path=file_path)
        db.session.add(protocol)
        db.session.commit()
        flash("Протокол добавлен", "success")
        return redirect(url_for("protocols.index"))
    return render_template("protocols/add.html")


@bp.route("/<int:id>")
@login_required
def detail(id):
    protocol = db.session.get(Protocol, id) or abort(404)
    payouts = protocol.payouts.order_by(Payout.date.desc()).all()
    return render_template("protocols/detail.html", protocol=protocol, payouts=payouts)


@bp.route("/<int:id>/pdf")
@login_required
def pdf(id):
    protocol = db.session.get(Protocol, id) or abort(404)
    if not protocol.file_path or not os.path.exists(protocol.file_path):
        abort(404)
    return send_file(
        protocol.file_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"protocol_{protocol.number}.pdf",
    )


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    protocol = db.session.get(Protocol, id) or abort(404)
    if protocol.file_path and os.path.exists(protocol.file_path):
        os.remove(protocol.file_path)

    for p in protocol.payouts:
        p.protocol_id = None

    db.session.delete(protocol)
    db.session.commit()
    flash("Протокол удалён", "success")
    return redirect(url_for("protocols.index"))
