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
    gender = db.Column(db.String(10), nullable=True)
    entry_date = db.Column(db.Date, nullable=False)
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
    helper_events = db.relationship("Event", secondary="event_helper", back_populates="helpers")

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

    events = db.relationship("Event", backref="protocol", lazy="dynamic")
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


class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    protocol_id = db.Column(db.Integer, db.ForeignKey("protocol.id"), nullable=True)
    file_path = db.Column(db.String(300), nullable=True)

    expenses = db.relationship(
        "EventExpense", backref="event", lazy="dynamic", cascade="all, delete-orphan"
    )
    helpers = db.relationship("Member", secondary="event_helper", back_populates="helper_events")

    @property
    def total_expenses(self):
        return sum((e.amount for e in self.expenses), 0)


class EventExpense(db.Model):
    __tablename__ = "event_expense"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    article = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)


event_helper = db.Table(
    "event_helper",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("member_id", db.Integer, db.ForeignKey("member.id"), primary_key=True),
)


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


class FinanceRecord(db.Model):
    __tablename__ = "finance_record"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), default="прочее")

    distributions = db.relationship(
        "FinanceRecordDistribution", backref="record", lazy="dynamic", cascade="all, delete-orphan"
    )


class FinanceDistributionRule(db.Model):
    __tablename__ = "finance_distribution_rule"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    percent = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)


class FinanceRecordDistribution(db.Model):
    __tablename__ = "finance_record_distribution"
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("finance_record.id"), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey("finance_distribution_rule.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    rule = db.relationship("FinanceDistributionRule")
