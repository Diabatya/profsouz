import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

SECRET_KEY = os.environ.get("SECRET_KEY", "profcom-local-secret-key-2026")
USERNAME = "admin"
PASSWORD = "admin"
DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PORT = 5000
