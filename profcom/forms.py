from flask_wtf import FlaskForm
from wtforms import FileField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from utils import title_name


class MemberForm(FlaskForm):
    full_name = StringField(
        "ФИО",
        validators=[DataRequired(), Length(min=2)],
        filters=[title_name],
    )
    department = StringField("Отдел", validators=[DataRequired()])
    position = StringField("Должность в профсоюзе", validators=[Optional()])
    phone = StringField("Телефон", validators=[Optional()])
    organization_position_id = SelectField(
        "Должность в организации",
        coerce=int,
        validators=[Optional()],
    )
    gender = SelectField(
        "Пол",
        choices=[
            ("auto", "Авто (по ФИО)"),
            ("male", "Мужской"),
            ("female", "Женский"),
        ],
    )
    birth_date = StringField("Дата рождения", validators=[DataRequired()])
    entry_date = StringField("Дата вступления", validators=[Optional()])
    photo = FileField("Фото профиля", validators=[Optional()])


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField("Текущий пароль", validators=[DataRequired()])
    new_password = PasswordField("Новый пароль", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Подтверждение пароля", validators=[DataRequired(), EqualTo("new_password")]
    )
