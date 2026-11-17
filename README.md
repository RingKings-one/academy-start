# Академия Старт

Демо: сайт + Telegram-бот для детской спортивной школы.

## Стек

- FastAPI + Uvicorn
- aiogram 3
- PostgreSQL + Alembic
- Docker Compose (api, bot, worker, db)

## Быстрый старт

```bash
cp .env.example .env
# заполните BOT_TOKEN, ADMIN_TELEGRAM_IDS, COACH_TELEGRAM_IDS

docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_demo.py
```

Сайт: http://localhost:8002/ (порт см. docker-compose)

## Роли

- **parent** — запись на пробное, расписание, оплаты (демо)
- **coach** — явка, занятия
- **admin** — заявки, слоты, тренеры, оплаты

`.env` в репозиторий не коммитится.
