import logging
import os
import sys
from datetime import date, timedelta

from flask import Flask, g, redirect, session, url_for
from flask_migrate import Migrate

import config
from models import (
    Admin,
    AnniversarySetting,
    DocumentTemplate,
    FinanceDistributionRule,
    Group,
    Organization,
    PayoutType,
    db,
)
from utils import login_required


def resource_path(relative_path):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


base_dir = config.BASE_DIR
app = Flask(
    __name__, template_folder=resource_path("templates"), static_folder=resource_path("static")
)
app.config.from_object("config")
app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "uploads")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.environ.get("DATABASE_URL")
    or app.config.get("DATABASE_URL")
    or "sqlite:///" + os.path.join(base_dir, "database.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

db.init_app(app)
migrate = Migrate(app, db, directory=resource_path("migrations"))


@app.template_filter("mask_phone")
def _mask_phone(value):
    if not value:
        return "-"
    s = str(value)
    if len(s) <= 4:
        return s
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


@app.template_filter("iso_date")
def _iso_date(value):
    return value.isoformat() if value else ""


log_path = os.path.join(base_dir, "app.log")
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info("Приложение запущено")


@app.template_filter("dt")
def dt_filter(value):
    if value:
        return value.strftime("%d.%m.%Y")
    return ""


@app.template_filter("money")
def money_filter(value):
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except Exception:
        return value


@app.before_request
def load_user():
    g.admin = None
    if "admin_id" in session:
        g.admin = db.session.get(Admin, session["admin_id"])


@app.route("/")
@login_required
def index():
    return redirect(url_for("main.dashboard"))


@app.context_processor
def utility_processor():
    from models import Organization

    return {"today": date.today, "current_org": Organization.get_or_create()}


def seed_data():
    if Admin.query.count() == 0:
        admin = Admin(username=config.USERNAME)
        admin.set_password(config.PASSWORD)
        db.session.add(admin)

    default_types = [
        ("Материальная помощь", 2000),
        ("Премия к празднику", 0),
        ("Подарок юбиляру", 0),
    ]
    for name, amount in default_types:
        if not PayoutType.query.filter_by(name=name).first():
            db.session.add(PayoutType(name=name, default_amount=amount))

    anniversaries = {
        20: 2000,
        25: 2500,
        30: 3000,
        35: 3500,
        40: 4000,
        45: 4500,
        50: 5000,
        55: 5500,
        60: 6000,
        65: 6500,
        70: 7000,
    }
    for age, amount in anniversaries.items():
        if not db.session.get(AnniversarySetting, age):
            db.session.add(AnniversarySetting(age=age, amount=amount))

    if not Group.query.filter_by(name="Профком", type="profkom").first():
        db.session.add(Group(name="Профком", type="profkom"))

    default_templates = [
        {
            "name": "Грамота",
            "type": "award",
            "title": "Грамота профсоюза",
            "body": """<div style="display:flex;align-items:center;justify-content:center;height:100%;box-sizing:border-box;padding:20px;">
  <div style="width:100%;border:14px double #b91c1c;border-radius:8px;background:linear-gradient(180deg,#fffbeb 0%,#ffffff 60%);padding:50px 40px;text-align:center;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
    <div style="font-size:90px;line-height:1;color:#f59e0b;margin-bottom:20px;">🎖️</div>
    <h1 style="font-size:52px;color:#b91c1c;text-transform:uppercase;letter-spacing:6px;margin:0 0 10px;">Грамота</h1>
    <p style="font-size:20px;color:#4b5563;margin-top:30px;">Награждается</p>
    <h2 style="font-size:36px;color:#111827;margin:25px 0;font-weight:bold;text-decoration:underline;text-decoration-color:#f59e0b;text-decoration-thickness:3px;">{{ member.full_name }}</h2>
    <p style="font-size:19px;color:#374151;line-height:1.6;max-width:90%;margin:0 auto 45px;">за активное участие в жизни профсоюзной организации,<br>добросовестный труд и высокий профессионализм.</p>
    <p style="font-size:16px;color:#6b7280;border-top:2px solid #e5e7eb;display:inline-block;padding-top:15px;">Дата выдачи: <strong style="color:#111827;">{{ issued_at|dt }}</strong></p>
  </div>
</div>""",
        },
        {
            "name": "Благодарственное письмо",
            "type": "letter",
            "title": "Благодарственное письмо",
            "body": """<div style="height:100%;box-sizing:border-box;padding:55px 60px;font-family:Georgia,serif;font-size:18px;line-height:1.7;color:#111827;background:#ffffff;">
  <div style="border-bottom:5px solid #1d4ed8;padding-bottom:18px;margin-bottom:55px;">
    <h2 style="color:#1e40af;margin:0;font-size:32px;">Благодарственное письмо</h2>
    <p style="color:#6b7280;margin:6px 0 0;font-size:14px;">профсоюзная организация</p>
  </div>
  <p style="text-align:right;color:#4b5563;margin-bottom:35px;">{{ issued_at|dt }}</p>
  <p>Выражаем искреннюю благодарность</p>
  <p style="font-size:26px;font-weight:bold;color:#1e3a8a;margin:22px 0;">{{ member.full_name }}</p>
  <p>за активное участие в работе профсоюзной организации, инициативу и поддержку коллег.</p>
  <p style="margin-top:90px;color:#374151;">Председатель профкома <span style="display:inline-block;width:240px;border-bottom:1px solid #111827;margin-left:10px;"></span></p>
</div>""",
        },
    ]
    for tpl in default_templates:
        if not DocumentTemplate.query.filter_by(name=tpl["name"]).first():
            db.session.add(DocumentTemplate(**tpl))

    Organization.get_or_create()

    if not FinanceDistributionRule.query.first():
        db.session.add(
            FinanceDistributionRule(
                name="Первичный профсоюз", percent=100, order=0, active=True, is_primary=True
            )
        )

    db.session.commit()


from routes import register_blueprints  # noqa: E402

register_blueprints(app)


def migrate_db():
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(db.engine)
        dialect = db.engine.dialect
        for table in db.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing_cols:
                    continue
                col_type = col.type.compile(dialect=dialect)
                sql = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
                try:
                    db.session.execute(text(sql))
                    app.logger.info("Добавлена колонка %s.%s", table.name, col.name)
                except Exception as col_e:
                    app.logger.warning("Не удалось добавить колонку %s.%s: %s", table.name, col.name, col_e)
        db.session.commit()
    except Exception as e:
        app.logger.warning("Миграция БД пропущена: %s", e)


def init_db():
    with app.app_context():
        from flask_migrate import stamp, upgrade
        from sqlalchemy import inspect

        tables = inspect(db.engine).get_table_names()
        if tables and "alembic_version" not in tables:
            # существующая БД без миграций — создаём схему и ставим метку
            db.create_all()
            migrate_db()
            stamp(revision="head")
        else:
            # пустая БД или уже под контролем alembic
            try:
                upgrade()
            except Exception:
                pass
            db.create_all()
            migrate_db()
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        seed_data()


def _should_init_db():
    if os.environ.get("PROFCOM_SKIP_INIT") == "1":
        return False
    # skip auto-init for flask migration CLI to prevent conflicts
    args = [a.lower() for a in sys.argv]
    if "db" in args and (
        "flask" in args or os.path.basename(sys.argv[0]).lower() in ("flask", "flask.exe")
    ):
        return False
    return True


if _should_init_db():
    try:
        init_db()
    except Exception:
        import traceback

        error_msg = traceback.format_exc()
        with open(os.path.join(base_dir, "startup_error.log"), "w", encoding="utf-8") as f:
            f.write(error_msg)
        print(error_msg, file=sys.stderr)
        raise


def _safe_port():
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            pass
    return app.config.get("PORT", 8765)


if __name__ == "__main__":
    try:
        port = _safe_port()
        print(f"Сервер запущен. Откройте http://<ip-адрес>:{port} (локально http://127.0.0.1:{port})")
        sys.stdout.flush()
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception:
        import traceback

        error_msg = traceback.format_exc()
        with open(os.path.join(base_dir, "startup_error.log"), "w", encoding="utf-8") as f:
            f.write(error_msg)
        print(error_msg, file=sys.stderr)
        raise
