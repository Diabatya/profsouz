import os
import uuid
from datetime import date

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from models import DocumentTemplate, Member, MemberAward, db
from utils import login_required, parse_date

bp = Blueprint("awards", __name__, url_prefix="/awards")


def _get_context(template, member, issued_at=None):
    return {
        "member": member,
        "today": date.today(),
        "issued_at": issued_at or date.today(),
        "template": template,
        "image_url": template.image_url,
    }


def _save_template_image(file):
    if not file or not file.filename:
        return None
    ext = os.path.splitext(secure_filename(file.filename).lower())[1]
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return None
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "templates")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(upload_dir, filename))
    return os.path.join("templates", filename).replace("\\", "/")


@bp.route("/")
@login_required
def index():
    templates = DocumentTemplate.query.filter_by(active=True).order_by(DocumentTemplate.order).all()
    awards = MemberAward.query.order_by(MemberAward.issued_at.desc()).limit(50).all()
    return render_template("awards/index.html", templates=templates, awards=awards)


@bp.route("/templates/add", methods=["POST"])
@login_required
def add_template():
    name = (request.form.get("name") or "").strip()
    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    image_path = _save_template_image(request.files.get("image"))
    if name and title and body:
        db.session.add(
            DocumentTemplate(
                name=name,
                type=request.form.get("type", "award"),
                title=title,
                body=body,
                image_path=image_path,
                order=request.form.get("order", type=int) or 0,
            )
        )
        db.session.commit()
        flash("Шаблон добавлен", "success")
    else:
        flash("Заполните название, заголовок и тело шаблона", "danger")
    return redirect(url_for("awards.index"))


@bp.route("/templates/<int:id>/edit", methods=["POST"])
@login_required
def edit_template(id):
    template = db.session.get(DocumentTemplate, id) or abort(404)
    template.name = (request.form.get("name") or "").strip()
    template.title = (request.form.get("title") or "").strip()
    template.body = (request.form.get("body") or "").strip()
    template.type = request.form.get("type", "award")
    template.order = request.form.get("order", type=int) or 0
    template.active = bool(request.form.get("active"))
    old_image_path = template.image_path
    new_image_path = _save_template_image(request.files.get("image"))
    if new_image_path:
        template.image_path = new_image_path
    if template.name and template.title and template.body:
        db.session.commit()
        if new_image_path and old_image_path:
            try:
                os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image_path))
            except OSError:
                pass
        flash("Шаблон обновлен", "success")
    else:
        flash("Заполните все поля", "danger")
    return redirect(url_for("awards.index"))


@bp.route("/templates/<int:id>/delete", methods=["POST"])
@login_required
def delete_template(id):
    template = db.session.get(DocumentTemplate, id) or abort(404)
    image_path = template.image_path
    db.session.delete(template)
    db.session.commit()
    if image_path:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], image_path))
        except OSError:
            pass
    flash("Шаблон удален", "success")
    return redirect(url_for("awards.index"))


@bp.route("/mass")
@login_required
def mass():
    templates = DocumentTemplate.query.filter_by(active=True).order_by(DocumentTemplate.order).all()
    members = Member.query.filter_by(status="active").order_by(Member.full_name).all()
    return render_template("awards/mass.html", templates=templates, members=members)


@bp.route("/mass/issue", methods=["POST"])
@login_required
def mass_issue():
    template_id = request.form.get("template_id", type=int)
    member_ids = [int(x) for x in request.form.getlist("member_ids") if x.isdigit()]
    issued_at = parse_date(request.form.get("issued_at")) or date.today()
    if not template_id or not member_ids:
        flash("Выберите шаблон и хотя бы одного члена", "danger")
        return redirect(url_for("awards.mass"))
    template = db.session.get(DocumentTemplate, template_id) or abort(404)
    members = Member.query.filter(Member.id.in_(member_ids)).all()
    for member in members:
        db.session.add(
            MemberAward(member_id=member.id, template_id=template.id, issued_at=issued_at)
        )
    db.session.commit()
    flash(f"Выдано {len(members)} наград", "success")
    return redirect(
        url_for("awards.print_preview", template_id=template.id, member_ids=",".join(str(m.id) for m in members))
    )


@bp.route("/print")
@login_required
def print_preview():
    template_id = request.args.get("template_id", type=int)
    member_ids = [int(x) for x in request.args.get("member_ids", "").split(",") if x.isdigit()]
    template = db.session.get(DocumentTemplate, template_id) or abort(404)
    members = Member.query.filter(Member.id.in_(member_ids)).order_by(Member.full_name).all()
    pages = []
    for member in members:
        award = (
            MemberAward.query.filter_by(member_id=member.id, template_id=template.id)
            .order_by(MemberAward.issued_at.desc())
            .first()
        )
        issued_at = award.issued_at if award else date.today()
        pages.append(template.render(_get_context(template, member, issued_at)))
    return render_template("awards/print.html", template=template, pages=pages, members=members)


@bp.route("/<int:id>/member_add", methods=["POST"])
@login_required
def member_add_award(id):
    member = db.session.get(Member, id) or abort(404)
    template_id = request.form.get("template_id", type=int)
    issued_at = parse_date(request.form.get("issued_at")) or date.today()
    note = (request.form.get("note") or "").strip() or None
    if template_id:
        db.session.add(
            MemberAward(member_id=member.id, template_id=template_id, issued_at=issued_at, note=note)
        )
        db.session.commit()
        flash("Награда добавлена", "success")
    else:
        flash("Выберите шаблон", "danger")
    return redirect(url_for("members.detail", id=member.id))


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_award(id):
    award = db.session.get(MemberAward, id) or abort(404)
    member_id = award.member_id
    db.session.delete(award)
    db.session.commit()
    flash("Награда удалена", "success")
    return redirect(url_for("members.detail", id=member_id))
