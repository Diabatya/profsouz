import os
import sys

if getattr(sys, "frozen", False):
    # PyInstaller bundle: keep data next to the executable
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "profcom-local-secret-key-2026")
USERNAME = "admin"
PASSWORD = "admin"
DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PORT = 8765
