from .auth import bp as auth_bp
from .birthdays import bp as birthdays_bp
from .inventory import bp as inventory_bp
from .main import bp as main_bp
from .members import bp as members_bp
from .payouts import bp as payouts_bp
from .protocols import bp as protocols_bp
from .reports import bp as reports_bp
from .settings import bp as settings_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(payouts_bp)
    app.register_blueprint(protocols_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(birthdays_bp)
    app.register_blueprint(settings_bp)
