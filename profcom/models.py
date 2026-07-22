from datetime import date

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class Admin(db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Member(db.Model):
    __tablename__ = "member"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=True)
    organization_position_id = db.Column(db.Integer, db.ForeignKey("position.id"), nullable=True)
    photo_path = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    entry_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="active")

    groups = db.relationship("Group", secondary="member_group", back_populates="members")
    organization_position = db.relationship(
        "Position", foreign_keys=[organization_position_id], backref="organization_members"
    )
    payouts = db.relationship(
        "Payout", backref="member", lazy="dynamic", cascade="all, delete-orphan"
    )
    status_history = db.relationship(
        "MemberStatusHistory",
        backref="member",
        lazy="dynamic",
        order_by="MemberStatusHistory.changed_at.desc()",
    )

    @property
    def is_active(self):
        return self.status == "active"

    @staticmethod
    def detect_gender(full_name):
        parts = full_name.split()
        if len(parts) >= 3:
            patronymic = parts[2].lower()
            if patronymic.endswith("на"):
                return "female"
            if patronymic.endswith("ич"):
                return "male"

        # Эвристика по имени, если отчества нет
        if len(parts) >= 2:
            first_name = parts[1].lower()
        elif len(parts) == 1:
            # Одно слово — не отличить имя от фамилии, не угадываем
            return None
        else:
            return None

        male_exceptions = {
            "саша",
            "паша",
            "маша",
            "миша",
            "жора",
            "коля",
            "толя",
            "воля",
            "слава",
            "вася",
            "гена",
            "витя",
            "сеня",
            "степа",
            "фома",
            "данила",
            "кузя",
            "илья",
            "никита",
            "кузьма",
            "петя",
            "ваня",
            "федя",
            "костя",
            "женя",
        }
        female_exceptions = {
            "любовь",
            "нинель",
            "рахиль",
            "эстер",
            "марион",
            "ирэн",
            "лейсан",
            "инес",
            "шахноз",
            "нур",
            "маргарет",
            "лейла",
        }
        if first_name in male_exceptions:
            return "male"
        if first_name in female_exceptions:
            return "female"
        if first_name[-1] in "аяь":
            return "female"
        if first_name[-1] in "бвгджзклмнпрстфхцчшщйоуеы":
            return "male"
        return None

    @property
    def gender_or_detect(self):
        return self.gender or self.detect_gender(self.full_name)

    @property
    def gender_display(self):
        return {"male": "Мужской", "female": "Женский"}.get(self.gender_or_detect, "Не указан")


member_group = db.Table(
    "member_group",
    db.Column("member_id", db.Integer, db.ForeignKey("member.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
)


class MemberChild(db.Model):
    __tablename__ = "member_child"
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)

    member = db.relationship("Member", backref="children")


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), default="other")
    members = db.relationship("Member", secondary=member_group, back_populates="groups")


class Position(db.Model):
    __tablename__ = "position"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    scope = db.Column(db.String(20), nullable=False, default="organization")
    level = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)


class PayoutType(db.Model):
    __tablename__ = "payout_type"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    default_amount = db.Column(db.Numeric(10, 2), default=0)

    categories = db.relationship(
        "PayoutCategory", backref="payout_type", lazy="dynamic", cascade="all, delete-orphan"
    )


class PayoutCategory(db.Model):
    __tablename__ = "payout_category"
    id = db.Column(db.Integer, primary_key=True)
    payout_type_id = db.Column(db.Integer, db.ForeignKey("payout_type.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), default=0)


class AnniversarySetting(db.Model):
    __tablename__ = "anniversary_setting"
    age = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), default=0)


class Protocol(db.Model):
    __tablename__ = "protocol"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    file_path = db.Column(db.String(300), nullable=True)

    payouts = db.relationship("Payout", backref="protocol", lazy="dynamic")


class Payout(db.Model):
    __tablename__ = "payout"
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey("payout_type.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("payout_category.id"), nullable=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey("protocol.id"), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    signed = db.Column(db.Boolean, default=False)

    type = db.relationship("PayoutType", backref="payouts")
    category = db.relationship("PayoutCategory", backref="payouts")


class MemberStatusHistory(db.Model):
    __tablename__ = "member_status_history"
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime, default=func.now())
    exit_date = db.Column(db.Date, nullable=True)
    note = db.Column(db.String(200), nullable=True)


class Dictionary(db.Model):
    __tablename__ = "dictionary"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(200), nullable=False)

    __table_args__ = (db.UniqueConstraint("type", "value", name="uq_dict_type_value"),)


class Organization(db.Model):
    __tablename__ = "organization"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(300), nullable=False, default="")
    short_name = db.Column(db.String(150), nullable=False, default="")
    address = db.Column(db.String(300), nullable=False, default="")
    phone = db.Column(db.String(50), nullable=False, default="")
    email = db.Column(db.String(100), nullable=False, default="")
    inn = db.Column(db.String(20), nullable=False, default="")
    kpp = db.Column(db.String(20), nullable=False, default="")
    ogrn = db.Column(db.String(30), nullable=False, default="")

    @classmethod
    def get_or_create(cls):
        org = cls.query.first()
        if not org:
            org = cls()
            db.session.add(org)
            db.session.commit()
        return org


class InventoryItem(db.Model):
    __tablename__ = "inventory_item"
    id = db.Column(db.Integer, primary_key=True)
    inventory_number = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit = db.Column(db.String(20), default="шт.")
    acquisition_date = db.Column(db.Date, nullable=True)
    warranty_term_years = db.Column(db.Integer, default=0)
    write_off_term_years = db.Column(db.Integer, default=0)
    location = db.Column(db.String(200), nullable=True)
    responsible_member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True)
    status = db.Column(db.String(20), default="active")
    file_path = db.Column(db.String(300), nullable=True)

    responsible = db.relationship("Member", backref="inventory_items")

    def _add_years(self, years):
        from datetime import timedelta

        if self.acquisition_date and years:
            try:
                return self.acquisition_date.replace(year=self.acquisition_date.year + years)
            except ValueError:
                return self.acquisition_date + timedelta(days=365 * years)
        return None

    @property
    def warranty_until(self):
        return self._add_years(self.warranty_term_years)

    @property
    def write_off_until(self):
        return self._add_years(self.write_off_term_years)

    @property
    def storage_until(self):
        return self.write_off_until


class UnionOfficer(db.Model):
    __tablename__ = "union_officer"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

    member = db.relationship("Member", backref="officer_roles")


class FinanceYear(db.Model):
    __tablename__ = "finance_year"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, unique=True)
    ppo_opening = db.Column(db.Numeric(12, 2), default=0)
    charity_opening = db.Column(db.Numeric(12, 2), default=0)
    mpo_percent = db.Column(db.Numeric(5, 2), default=15)
    opo_percent = db.Column(db.Numeric(5, 2), default=10)
    ppo_percent = db.Column(db.Numeric(5, 2), default=70)
    charity_percent = db.Column(db.Numeric(5, 2), default=5)
    note = db.Column(db.String(300), nullable=True)

    months = db.relationship(
        "FinanceMonth", backref="year", lazy="dynamic", cascade="all, delete-orphan"
    )
    expenses = db.relationship(
        "FinanceExpense", backref="year", lazy="dynamic", cascade="all, delete-orphan"
    )
    commissions = db.relationship(
        "FinanceCommission", backref="year", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def total_opening(self):
        return self.ppo_opening + self.charity_opening

    @property
    def percent_total(self):
        return self.mpo_percent + self.opo_percent + self.ppo_percent + self.charity_percent


class FinanceMonth(db.Model):
    __tablename__ = "finance_month"
    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("finance_year.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    gross_amount = db.Column(db.Numeric(12, 2), default=0)
    mpo_amount = db.Column(db.Numeric(12, 2), default=0)
    opo_amount = db.Column(db.Numeric(12, 2), default=0)
    ppo_amount = db.Column(db.Numeric(12, 2), default=0)
    charity_amount = db.Column(db.Numeric(12, 2), default=0)
    date_received = db.Column(db.Date, nullable=True)

    __table_args__ = (db.UniqueConstraint("year_id", "month", name="uq_finance_month_year_month"),)


class FinanceExpense(db.Model):
    __tablename__ = "finance_expense"
    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("finance_year.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    fund = db.Column(db.String(20), nullable=False, default="ppo")
    protocol_number = db.Column(db.String(50), nullable=True)
    protocol_date = db.Column(db.Date, nullable=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey("protocol.id"), nullable=True)
    description = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())

    __table_args__ = (
        db.CheckConstraint("fund IN ('ppo', 'charity')", name="ck_finance_expense_fund"),
    )
    protocol = db.relationship("Protocol", backref="finance_expenses")


class FinanceCommission(db.Model):
    __tablename__ = "finance_commission"
    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("finance_year.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())
