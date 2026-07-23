import os
import re
import shutil
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from io import BytesIO

from flask import flash, g, redirect, request, send_file, session, url_for
from openpyxl import Workbook

from models import Admin, Dictionary, db


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("auth.login"))
        admin = db.session.get(Admin, session["admin_id"])
        if not admin:
            session.pop("admin_id", None)
            return redirect(url_for("auth.login"))
        g.is_readonly = admin.is_readonly()
        if request.method != "GET" and g.is_readonly:
            flash("У вас режим только чтения", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)

    return decorated


def parse_date(s):
    if not s:
        return None
    if isinstance(s, date):
        return s
    if isinstance(s, datetime):
        return s.date()
    s = str(s).strip()
    for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(s):
    if s is None:
        return Decimal(0)
    try:
        return Decimal(str(s).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def title_name(value):
    """Приводит ФИО/название к виду 'Иванов Иван Иванович'."""
    if not value:
        return value
    name = str(value).strip()
    name = re.sub(r"\s+", " ", name)
    return name.title()


def _normalize_value(value):
    """Нормализация для сравнения значений справочника (без учёта регистра и ё/е)."""
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("ё", "е"))


def dictionary_values(dtype):
    """Возвращает отсортированный список значений справочника заданного типа."""
    return [
        d.value for d in Dictionary.query.filter_by(type=dtype).order_by(Dictionary.value).all()
    ]


def save_dictionary_value(dtype, value):
    """Добавляет новое значение в справочник, если его ещё нет."""
    if not value:
        return None
    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    if not value:
        return None
    normalized = _normalize_value(value)
    for existing in Dictionary.query.filter_by(type=dtype).all():
        if _normalize_value(existing.value) == normalized:
            return existing.value
    entry = Dictionary(type=dtype, value=value)
    db.session.add(entry)
    db.session.commit()
    return value


def excel_response(headers, rows, filename="report.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(list(row))
    for col in ws.columns:
        col_letter = col[0].column_letter
        max_len = 0
        for cell in col:
            try:
                max_len = max(max_len, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 2, 50)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


def period_bounds(period):
    today = date.today()
    if period == "month":
        return today.replace(day=1), today
    if period == "quarter":
        month = (today.month - 1) // 3 * 3 + 1
        return today.replace(month=month, day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    return None, None


def apply_sort(query, sort, order, model, allowed):
    if sort in allowed:
        col = getattr(model, sort)
        if order == "desc":
            col = col.desc()
        query = query.order_by(col)
    return query


def backup_database(db_path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    shutil.copy(db_path, tmp.name)
    data = open(tmp.name, "rb").read()
    os.remove(tmp.name)
    return send_file(
        BytesIO(data),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=f"backup_{ts}.db",
    )
