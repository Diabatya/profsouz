import logging
import os
import sys
from datetime import date, timedelta

from flask import Flask, g, redirect, session, url_for
from flask_migrate import Migrate

import config
from models import Admin, AnniversarySetting, DocumentTemplate, Group, PayoutType, db
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
    return {"today": date.today}


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
            "body": """<div style="text-align:center; padding: 60px 40px; border: 8px double #c00; height: 100%; box-sizing: border-box;">
  <h1 style="font-size: 42px; color: #c00; margin-bottom: 40px;">Грамота</h1>
  <p style="font-size: 20px;">Награждается</p>
  <h2 style="font-size: 32px; margin: 30px 0; text-decoration: underline;">{{ member.full_name }}</h2>
  <p style="font-size: 18px; line-height: 1.6;">за активное участие в жизни профсоюзной организации,<br>добросовестный труд и высокий профессионализм.</p>
  <p style="margin-top: 60px; font-size: 16px;">Дата выдачи: {{ issued_at|dt }}</p>
</div>""",
        },
        {
            "name": "Благодарственное письмо",
            "type": "letter",
            "title": "Благодарственное письмо",
            "body": """<div style="padding: 60px 50px; font-size: 18px; line-height: 1.6;">
  <p style="text-align: right;">{{ today|dt }}</p>
  <h2 style="text-align: center; margin-bottom: 40px;">Благодарственное письмо</h2>
  <p>Выражаем искреннюю благодарность</p>
  <p style="font-weight: bold; font-size: 22px; margin: 20px 0;">{{ member.full_name }}</p>
  <p>за активное участие в работе профсоюзной организации, инициативу и поддержку коллег.</p>
  <p style="margin-top: 60px;">Председатель профкома _________________</p>
</div>""",
        },
    ]
    for tpl in default_templates:
        if not DocumentTemplate.query.filter_by(name=tpl["name"]).first():
            db.session.add(DocumentTemplate(**tpl))

    db.session.commit()


from routes import register_blueprints  # noqa: E402

register_blueprints(app)


def migrate_db():
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(db.engine)
        cols = [c["name"] for c in inspector.get_columns("member")]
        if "photo_path" not in cols:
            db.session.execute(text("ALTER TABLE member ADD COLUMN photo_path VARCHAR(255)"))
        if "gender" not in cols:
            db.session.execute(text("ALTER TABLE member ADD COLUMN gender VARCHAR(10)"))
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
                # fallback, если миграций нет
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
    init_db()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else app.config.get("PORT", 8765)
    print(f"Сервер запущен. Откройте http://<ip-адрес>:{port} (локально http://127.0.0.1:{port})")
    app.run(host="0.0.0.0", port=port, debug=False)
