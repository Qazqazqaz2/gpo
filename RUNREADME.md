### GPO My — быстрый запуск (Windows)

Ниже — минимальные шаги, чтобы любой человек смог установить и запустить проект локально на Windows (PowerShell).

---

## Быстрый старт (TL;DR)
1) Установите: Python 3.11+ и PostgreSQL 14+.
2) Создайте БД `gpo_practice` и пользователя/пароль под строку подключения.
3) В PowerShell выполните:
```powershell
cd C:\Users\armian\Desktop\Works\gpo_my
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt  # если файла нет, см. раздел «Если нет requirements.txt»
python app.py
```
4) Откройте `http://127.0.0.1:5000`.

---

## Требования
- Python 3.11 или новее
- PostgreSQL 14 или новее (локально)
- PowerShell (Windows)

---

## Настройка базы данных
В `app.py` по умолчанию задана строка подключения:
```
postgresql://postgres:762341@localhost/gpo_practice
```
Есть два варианта:
- Оставить как есть и создать в PostgreSQL пользователя `postgres` с паролем `762341` и базу `gpo_practice`;
- Или изменить строку подключения в `app.py` под свои учётные данные.

Создание БД (пример через psql):
```powershell
psql -U postgres -h localhost -c "CREATE DATABASE gpo_practice;"
```
Если используете другой пользователь/пароль — не забудьте скорректировать URI в `app.py`.

Примечание: при первом запуске приложение само создаст таблицы и базовые роли.

---

## Установка зависимостей
Рекомендуемый способ — через виртуальное окружение:
```powershell
cd C:\Users\armian\Desktop\Works\gpo_my
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

- Если в репозитории есть `requirements.txt`:
```powershell
pip install -r requirements.txt
```

- Если файла `requirements.txt` нет, установите основные пакеты вручную:
```powershell
pip install \
  flask \
  flask_sqlalchemy \
  flask_login \
  flask_migrate \
  psycopg2-binary \
  reportlab \
  pypdf \
  python-docx
```
При необходимости дополнительно установите:
```powershell
pip install python-dotenv gunicorn
```

---

## Запуск приложения (разработка)
```powershell
.\.venv\Scripts\Activate.ps1  # если ещё не активировано
python app.py
```
Приложение по умолчанию стартует на `http://127.0.0.1:5000`.

---

## Типовой продакшн-запуск (информация)
В `app.py` приведены примеры для WSGI-серверов. На локальной машине это не требуется, но для справки:
- gunicorn: `gunicorn -w 4 -b 0.0.0.0:5000 --backlog 1024 app:app`
- uWSGI: `uwsgi --socket 0.0.0.0:5000 --protocol=http --processes 4 --threads 2 --listen 1024 --module app:app`

---

## Частые проблемы
- Не удаётся подключиться к PostgreSQL: проверьте, что служба PostgreSQL запущена, БД `gpo_practice` создана, а строка подключения в `app.py` соответствует вашим логину/паролю/хосту/БД.
- Ошибка компиляции `psycopg2` на Windows: используйте пакет `psycopg2-binary` (он указан выше).
- Отсутствуют шаблоны/статические файлы/документы: убедитесь, что все файлы из репозитория присутствуют локально; проект использует шаблоны HTML и DOCX для генерации PDF.

---

## Структура (важное)
- `app.py` — точка входа Flask-приложения, регистрация blueprints, настройки БД и базовых ролей.
- `routes/` — модули с маршрутами (`auth`, `main`).
- `models.py` — модели SQLAlchemy (пользователи, роли, студенты и пр.).
- `extensions.py` — инициализация `db`, `migrate`, `login_manager`.
- `templates/` — HTML-шаблоны.
- DOCX-шаблон заявления используется для PDF-генерации внутри `routes/main.py`.

---

## Поддержка
Если что-то не запускается, укажите:
- Версию Python (`python --version`)
- Версию PostgreSQL
- Точный текст ошибки из консоли PowerShell
Это позволит быстрее помочь.

