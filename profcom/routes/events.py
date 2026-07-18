import os
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from models import Event, EventExpense, Member, Protocol, db
from utils import (
    apply_sort,
    dictionary_values,
    login_required,
    parse_date,
    parse_decimal,
    save_dictionary_value,
)

bp = Blueprint("events", __name__, url_prefix="/events")


def allowed_pdf(filename):
    return filename and filename.lower().endswith(".pdf")


@bp.route("/")
@login_required
def index():
    q = Event.query
    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    q = apply_sort(q, sort, order, Event, ["date", "name"])
    pagination = q.paginate(page=page, per_page=max(per_page, 5), error_out=False)
    return render_template(
        "events/list.html",
        events=pagination.items,
        pagination=pagination,
        sort=sort,
        order=order,
        per_page=per_page,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    protocols = Protocol.query.order_by(Protocol.date.desc()).all()
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    article_options = dictionary_values("event_article")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        edate = parse_date(request.form.get("date"))
        protocol_id = request.form.get("protocol_id") or None
        protocol_id = int(protocol_id) if protocol_id else None
        file = request.files.get("file")

        if not name or not edate:
            flash("Укажите название и дату мероприятия", "danger")
            return render_template(
                "events/add.html",
                protocols=protocols,
                members=members,
                article_options=article_options,
            )

        file_path = None
        if file and allowed_pdf(file.filename):
            filename = f"{uuid4()}.pdf"
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

        event = Event(name=name, date=edate, protocol_id=protocol_id, file_path=file_path)
        db.session.add(event)
        db.session.flush()

        posted_articles = request.form.getlist("article[]")
        posted_amounts = request.form.getlist("amount[]")
        for article, amount in zip(posted_articles, posted_amounts, strict=False):
            if article.strip():
                article = save_dictionary_value("event_article", article.strip()) or article.strip()
                db.session.add(
                    EventExpense(event_id=event.id, article=article, amount=parse_decimal(amount))
                )

        helper_ids = request.form.getlist("helper_ids[]")
        for hid in helper_ids:
            if hid:
                member = db.session.get(Member, int(hid))
                if member:
                    event.helpers.append(member)

        db.session.commit()
        flash("Мероприятие добавлено", "success")
        return redirect(url_for("events.index"))

    return render_template(
        "events/add.html", protocols=protocols, members=members, article_options=article_options
    )


@bp.route("/<int:id>")
@login_required
def detail(id):
    event = db.session.get(Event, id) or abort(404)
    return render_template("events/detail.html", event=event)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    event = db.session.get(Event, id) or abort(404)
    if event.file_path and os.path.exists(event.file_path):
        os.remove(event.file_path)
    event.helpers = []
    db.session.delete(event)
    db.session.commit()
    flash("Мероприятие удалено", "success")
    return redirect(url_for("events.index"))


@bp.route("/<int:id>/pdf")
@login_required
def pdf(id):
    from flask import abort, send_file

    event = db.session.get(Event, id) or abort(404)
    if not event.file_path or not os.path.exists(event.file_path):
        abort(404)
    return send_file(
        event.file_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"event_{event.name}.pdf",
    )
