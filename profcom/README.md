# Профсоюз — приложение для управления профсоюзной организацией

## Автономная работа

Приложение работает полностью автономно: на целевом компьютере не требуется Python, интернет и установленные библиотеки. Все зависимости (Flask, SQLAlchemy, openpyxl, Werkzeug и др.) упаковываются внутрь единого exe-файла при сборке через PyInstaller.

Bootstrap CSS, JS, иконки, шаблоны и `config.py` также включаются в exe, поэтому приложение не обращается к CDN и не требует внешних ресурсов.

## Запуск на машине разработчика (macOS / Linux / Windows с Python)

```bash
cd profcom
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Откройте в браузере http://127.0.0.1:5000.

Логин по умолчанию: `admin` / `admin`.

## Сборка одного exe для Windows

Сборка выполняется **на машине разработчика/сборщика**, где есть Python и (желательно) интернет для загрузки пакетов. На целевом сервере Windows интернет не требуется.

### Вариант 1. Сборка на машине с интернетом

```bash
pip install -r requirements.txt
pyinstaller build.spec
```

### Вариант 2. Сборка на машине без интернета (предварительно скачать пакеты)

На машине с интернетом выполните:

```bash
pip download -r requirements.txt -d packages --only-binary=:all: --platform win_amd64
```

Перенесите папку `packages` и проект на автономный ПК и установите:

```bash
pip install --no-index --find-links=packages -r requirements.txt
pyinstaller build.spec
```

Или вручную:

```bash
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" --add-data "config.py;." app.py
```

### Перенос на сервер

1. Возьмите `dist/profcom.exe`.
2. Поместите его в нужную папку на целевом ПК Windows.
3. Рядом с `profcom.exe` при первом запуске автоматически создадутся `database.db` и папка `uploads`.
4. Запустите `profcom.exe`. В консоли появится `Сервер запущен. Откройте http://127.0.0.1:5000`.

## Особенности

- Все данные хранятся в `database.db` (SQLite), рядом с исполняемым файлом.
- PDF-файлы сохраняются в папку `uploads`.
- Бэкап базы данных доступен в разделе «Настройки».
- Пароль администратора хранится в базе данных, меняется через «Настройки».
