import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Member


def test_detect_gender_by_patronymic_male():
    assert Member.detect_gender("Иванов Иван Иванович") == "male"
    assert Member.detect_gender("Петров Петр Петрович") == "male"


def test_detect_gender_by_patronymic_female():
    assert Member.detect_gender("Иванова Мария Ивановна") == "female"
    assert Member.detect_gender("Петрова Анна Петровна") == "female"
    assert Member.detect_gender("Ильина Анна Ильинична") == "female"


def test_detect_gender_no_patronymic():
    # по имени: Мария -> жен. (кончается на я)
    assert Member.detect_gender("Иванова Мария") == "female"
    # по имени: Иван -> муж. (согласный на конце)
    assert Member.detect_gender("Иванов Иван") == "male"
    # исключение: Саша -> муж.
    assert Member.detect_gender("Сидоров Саша") == "male"
    # исключение: Любовь -> жен.
    assert Member.detect_gender("Смирнова Любовь") == "female"
    # одно слово — не угадываем
    assert Member.detect_gender("Сидоров") is None


def test_gender_or_detect_stored_value():
    m = Member(full_name="Иванов Иван Иванович", gender="female")
    assert m.gender_or_detect == "female"


def test_gender_or_detect_falls_back_to_detection():
    m = Member(full_name="Иванова Мария Ивановна")
    assert m.gender_or_detect == "female"


def test_gender_display():
    m = Member(full_name="Иванов Иван Иванович", gender="male")
    assert m.gender_display == "Мужской"
    m2 = Member(full_name="Иванова Мария Ивановна")
    assert m2.gender_display == "Женский"
    m3 = Member(full_name="Иванов Иван")
    assert m3.gender_display == "Мужской"
    m4 = Member(full_name="Сидоров")
    assert m4.gender_display == "Не указан"
