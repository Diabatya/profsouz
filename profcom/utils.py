import os
import shutil
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from io import BytesIO

from flask import redirect, send_file, session, url_for
from openpyxl import Workbook


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_decimal(s):
    if s is None:
        return Decimal(0)
    try:
        return Decimal(str(s).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(0)


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
