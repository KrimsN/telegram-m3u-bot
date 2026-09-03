# telegram-m3u-bot

Telegram-бот, деплой на Replit.

## Стек

- Python >= 3.12, зависимости и виртуальное окружение — через `uv` (`pyproject.toml`, `uv.lock`).
- Точка входа: `main.py`.

## Конфигурация

- Токен бота хранится в `.env` (переменная `TELEGRAM_BOT_TOKEN`), файл не коммитится (см. `.gitignore`).
- `.env.example` — шаблон переменных окружения для новых окружений/Replit Secrets.

## Replit

- На Replit переменные окружения задаются через Secrets, а не `.env` — при деплое перенести `TELEGRAM_BOT_TOKEN` туда.

## Команды

```bash
uv sync              # установить зависимости
uv run main.py        # запустить бота
uv add <package>      # добавить зависимость
```
