from time import time

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models import Admin

bp = Blueprint("auth", __name__, url_prefix="/")

_login_attempts = {}


def _check_rate_limit(ip):
    now = time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < 900]
    _login_attempts[ip] = attempts
    return len(attempts) < 5


def _record_failed_login(ip):
    _login_attempts.setdefault(ip, []).append(time())


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ip = request.remote_addr or "unknown"
        if not _check_rate_limit(ip):
            flash("Слишком много попыток входа. Попробуйте через 15 минут.", "danger")
            return render_template("login.html")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session["admin_id"] = admin.id
            _login_attempts.pop(ip, None)
            return redirect(url_for("main.dashboard"))
        _record_failed_login(ip)
        flash("Неверный логин или пароль", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.pop("admin_id", None)
    return redirect(url_for("auth.login"))
