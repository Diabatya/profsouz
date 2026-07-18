import os
import shutil

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

import config
from models import Admin, AnniversarySetting, PayoutType, db
from utils import login_required, parse_decimal

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/")
@login_required
def index():
    from forms import ChangePasswordForm

    payout_types = PayoutType.query.order_by(PayoutType.name).all()
    anniversaries = AnniversarySetting.query.order_by(AnniversarySetting.age).all()
    return render_template(
        "settings.html",
        payout_types=payout_types,
        anniversaries=anniversaries,
        change_password_form=ChangePasswordForm(),
    )


@bp.route("/payout_types/add", methods=["POST"])
@login_required
def add_payout_type():
    name = request.form.get("name", "").strip()
    amount = parse_decimal(request.form.get("default_amount", "0"))
    if name:
        if PayoutType.query.filter_by(name=name).first():
            flash("Тип выплаты с таким названием уже есть", "danger")
        else:
            db.session.add(PayoutType(name=name, default_amount=amount))
            db.session.commit()
            flash("Тип выплаты добавлен", "success")
    else:
        flash("Укажите название", "danger")
    return redirect(url_for("settings.index"))


@bp.route("/payout_types/<int:id>/edit", methods=["POST"])
@login_required
def edit_payout_type(id):
    ptype = db.session.get(PayoutType, id) or abort(404)
    name = request.form.get("name", "").strip()
    amount = parse_decimal(request.form.get("default_amount", "0"))
    if name:
        ptype.name = name
        ptype.default_amount = amount
        db.session.commit()
        flash("Тип выплаты обновлён", "success")
    else:
        flash("Укажите название", "danger")
    return redirect(url_for("settings.index"))


@bp.route("/payout_types/<int:id>/delete", methods=["POST"])
@login_required
def delete_payout_type(id):
    ptype = db.session.get(PayoutType, id) or abort(404)
    db.session.delete(ptype)
    db.session.commit()
    flash("Тип выплаты удалён", "success")
    return redirect(url_for("settings.index"))


@bp.route("/anniversaries/save", methods=["POST"])
@login_required
def save_anniversaries():
    age = request.form.get("age", type=int)
    amount = parse_decimal(request.form.get("amount", "0"))
    if age and age > 0:
        setting = db.session.get(AnniversarySetting, age)
        if setting:
            setting.amount = amount
        else:
            db.session.add(AnniversarySetting(age=age, amount=amount))
    new_age = request.form.get("new_age", type=int)
    new_amount = parse_decimal(request.form.get("new_amount", "0"))
    if new_age and new_age > 0:
        if not db.session.get(AnniversarySetting, new_age):
            db.session.add(AnniversarySetting(age=new_age, amount=new_amount))
        else:
            flash("Этот возраст уже есть в списке", "warning")
    db.session.commit()
    flash("Настройки юбилеев сохранены", "success")
    return redirect(url_for("settings.index"))


@bp.route("/anniversaries/<int:age>/delete", methods=["POST"])
@login_required
def delete_anniversary(age):
    setting = db.session.get(AnniversarySetting, age) or abort(404)
    db.session.delete(setting)
    db.session.commit()
    flash("Юбилейная дата удалена", "success")
    return redirect(url_for("settings.index"))


@bp.route("/change_password", methods=["POST"])
@login_required
def change_password():
    from forms import ChangePasswordForm

    form = ChangePasswordForm()
    admin = db.session.get(Admin, session.get("admin_id"))
    if form.validate_on_submit():
        if not admin or not admin.check_password(form.old_password.data):
            flash("Неверный текущий пароль", "danger")
        else:
            admin.set_password(form.new_password.data)
            db.session.commit()
            flash("Пароль изменён", "success")
    else:
        for field, errors in form.errors.items():
            for e in errors:
                flash(f"{getattr(form, field).label.text}: {e}", "danger")
    return redirect(url_for("settings.index"))


@bp.route("/backup")
@login_required
def backup():
    from utils import backup_database

    db_path = os.path.join(config.BASE_DIR, "database.db")
    return backup_database(db_path)


@bp.route("/restore", methods=["POST"])
@login_required
def restore():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".db"):
        flash("Выберите файл базы данных (.db)", "danger")
        return redirect(url_for("settings.index"))
    db_path = os.path.join(config.BASE_DIR, "database.db")
    try:
        shutil.copy(db_path, db_path + ".bak")
    except FileNotFoundError:
        pass
    db.session.remove()
    db.engine.dispose()
    file.save(db_path)
    flash("База данных восстановлена. Рекомендуется перезапустить приложение.", "success")
    return redirect(url_for("settings.index"))
