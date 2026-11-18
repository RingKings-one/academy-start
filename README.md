# Академия Старт — демо (сайт + Telegram-бот)

## Стек
- Python 3.12
- FastAPI
- aiogram 3
- PostgreSQL 16
- SQLAlchemy 2 + Alembic
- Docker Compose

## Быстрый старт (локально)

1. Скопируй `.env.example` → `.env` и укажи:
   - `BOT_TOKEN`
   - `ADMIN_TELEGRAM_IDS` (свой telegram_id)
   - при необходимости `COACH_TELEGRAM_IDS`

2. Подними базу:
```bash
docker compose up -d db
```

3. Установи зависимости (если без Docker для api/bot):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Примени миграции (когда появятся):
```bash
alembic upgrade head
```

5. Запуск:
```bash
# API
uvicorn app.main:app --reload --port 8000

# Bot
python -m app.bot.main

# Worker
python -m app.worker.main
```

Или всё через Docker:
```bash
docker compose up --build
```

## Порты
- API: 8000
- Сайт (позже): 3001
- Postgres: 5432

## Структура
```
app/
  api/          # FastAPI роуты
  bot/          # aiogram бот
  core/         # конфиг
  db/           # модели + миграции
  services/     # бизнес-логика
  worker/       # очередь reminders
frontend/       # сайт
scripts/        # seed, reset-demo
```
