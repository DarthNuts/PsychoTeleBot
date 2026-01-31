# Подключение PsychoTeleBot к Telegram

Пошаговая инструкция по интеграции бота с Telegram API.

---

## 📋 Содержание

1. [Создание бота в Telegram](#1-создание-бота-в-telegram)
2. [Установка зависимостей](#2-установка-зависимостей)
3. [Создание Telegram адаптера](#3-создание-telegram-адаптера)
4. [Настройка конфигурации](#4-настройка-конфигурации)
5. [Запуск бота](#5-запуск-бота)
6. [Деплой](#6-деплой)

---

## 1. Создание бота в Telegram

### Шаг 1.1: Открыть BotFather

1. Откройте Telegram
2. Найдите бота [@BotFather](https://t.me/botfather)
3. Нажмите "Start"

### Шаг 1.2: Создать нового бота

Отправьте команду:
```
/newbot
```

### Шаг 1.3: Задать имя бота

BotFather попросит указать:

1. **Отображаемое имя** (например, "PsychoTeleBot"):
   ```
   PsychoTeleBot
   ```

2. **Username** (должен заканчиваться на "bot", например, "psycho_support_bot"):
   ```
   psycho_support_bot
   ```

### Шаг 1.4: Сохранить токен

BotFather пришлет вам сообщение с **токеном**:
```
Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567
```

**⚠️ ВАЖНО:** Храните токен в секрете! Не публикуйте его в репозитории.

### Шаг 1.5: Настроить команды бота (опционально)

Отправьте команду в BotFather:
```
/setcommands
```

Выберите вашего бота и введите список команд:
```
start - Начать работу с ботом
menu - Главное меню
clear - Очистить контекст ИИ
help - Помощь
```

---

## 2. Установка зависимостей

### Вариант A: python-telegram-bot (рекомендуется)

Обновите `requirements.txt`:
```bash
pytest>=7.4.0
python-telegram-bot>=20.7
python-dotenv>=1.0.0
```

Установите зависимости:
```bash
pip install -r requirements.txt
```

### Вариант B: aiogram (альтернатива)

```bash
pip install aiogram>=3.3.0 python-dotenv>=1.0.0
```

**В этой инструкции используется python-telegram-bot.**

---

## 3. Создание Telegram адаптера

### Шаг 3.1: Создать структуру

Создайте директорию для Telegram адаптера:
```bash
mkdir adapters/telegram
```

### Шаг 3.2: Создать файл конфигурации

Создайте `adapters/telegram/__init__.py`:
```python
# Telegram adapter
```

### Шаг 3.3: Создать основной файл бота

Создайте `adapters/telegram/bot.py`:

```python
"""
Telegram адаптер для PsychoTeleBot
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.in_memory_repositories import (
    InMemorySessionRepository,
    InMemoryTicketRepository
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram адаптер для PsychoTeleBot"""

    def __init__(self, token: str):
        """
        Инициализация Telegram бота
        
        Args:
            token: Токен бота от BotFather
        """
        self.token = token
        
        # Инициализация бизнес-логики
        session_repo = InMemorySessionRepository()
        ticket_repo = InMemoryTicketRepository()
        state_machine = StateMachine()
        
        self.bot_service = BotService(
            session_repo=session_repo,
            ticket_repo=ticket_repo,
            state_machine=state_machine
        )
        
        # Создание приложения
        self.application = Application.builder().token(token).build()
        
        # Регистрация обработчиков
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        
        # Команда /start
        self.application.add_handler(
            CommandHandler("start", self.handle_start)
        )
        
        # Команда /menu
        self.application.add_handler(
            CommandHandler("menu", self.handle_menu)
        )
        
        # Команда /clear
        self.application.add_handler(
            CommandHandler("clear", self.handle_clear)
        )
        
        # Команда /help
        self.application.add_handler(
            CommandHandler("help", self.handle_help)
        )
        
        # Все текстовые сообщения
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/start")
        await update.message.reply_text(response)
        
        logger.info(f"User {user_id} started the bot")

    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /menu"""
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/menu")
        await update.message.reply_text(response)

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /clear"""
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/clear")
        await update.message.reply_text(response)

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_text = """
🤖 *PsychoTeleBot - Помощь*

Доступные команды:
/start - Начать работу с ботом
/menu - Вернуться в главное меню
/clear - Очистить контекст диалога с ИИ
/help - Показать эту справку

Бот предоставляет:
• Консультации со специалистами
• Консультации с ИИ-ассистентом
• Ответы на вопросы по психологии
• Анонимность и конфиденциальность
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = str(update.effective_user.id)
        message = update.message.text
        
        logger.info(f"User {user_id}: {message}")
        
        # Обработка через бизнес-логику
        response = self.bot_service.process_message(user_id, message)
        
        await update.message.reply_text(response)
        
        logger.info(f"Bot response sent to {user_id}")

    def run(self):
        """Запуск бота"""
        logger.info("Starting PsychoTeleBot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot stopped")
```

### Шаг 3.4: Создать точку входа

Создайте `adapters/telegram/run.py`:

```python
"""
Точка входа для запуска Telegram бота
"""

import os
from dotenv import load_dotenv
from adapters.telegram.bot import TelegramBot


def main():
    """Запуск Telegram бота"""
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение токена
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден!")
        print("Создайте файл .env и добавьте в него:")
        print("TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather")
        return
    
    # Создание и запуск бота
    bot = TelegramBot(token)
    bot.run()


if __name__ == "__main__":
    main()
```

---

## 4. Настройка конфигурации

### Шаг 4.1: Создать .env файл

Создайте файл `.env` в корне проекта:
```bash
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567

# Optional: Database URL (если используете БД)
# DATABASE_URL=sqlite:///bot.db
```

**⚠️ ВАЖНО:** Добавьте `.env` в `.gitignore` (уже добавлено).

### Шаг 4.2: Проверить .gitignore

Убедитесь, что `.env` в `.gitignore`:
```gitignore
# Telegram bot token (if you add it later)
.env
config.ini
```

### Шаг 4.3: Создать example файл

Создайте `.env.example` для документации:
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_token_here

# Database (optional)
# DATABASE_URL=sqlite:///bot.db
```

---

## 5. Запуск бота

### Шаг 5.1: Обновить requirements.txt

Убедитесь, что все зависимости добавлены:
```
pytest>=7.4.0
python-telegram-bot>=20.7
python-dotenv>=1.0.0
```

### Шаг 5.2: Установить зависимости

```bash
pip install -r requirements.txt
```

### Шаг 5.3: Настроить токен

Отредактируйте `.env` и добавьте ваш токен:
```bash
TELEGRAM_BOT_TOKEN=ваш_реальный_токен
```

### Шаг 5.4: Запустить бота

```bash
python -m adapters.telegram.run
```

Или создайте скрипт запуска `run_telegram.bat` (Windows):
```batch
@echo off
echo Starting PsychoTeleBot for Telegram...
python -m adapters.telegram.run
pause
```

Или `run_telegram.sh` (Linux/Mac):
```bash
#!/bin/bash
echo "Starting PsychoTeleBot for Telegram..."
python -m adapters.telegram.run
```

### Шаг 5.5: Проверить работу

1. Откройте Telegram
2. Найдите вашего бота по username
3. Нажмите "Start"
4. Отправьте `/start`

Вы должны увидеть приветственное сообщение!

---

## 6. Деплой

### Вариант A: Запуск на сервере (Linux)

#### 1. Установить на сервер

```bash
# Клонировать репозиторий
git clone https://github.com/DarthNuts/PsychoTeleBot.git
cd PsychoTeleBot

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
nano .env
# Добавьте TELEGRAM_BOT_TOKEN=...
```

#### 2. Запустить как сервис (systemd)

Создайте файл `/etc/systemd/system/psychotelebot.service`:

```ini
[Unit]
Description=PsychoTeleBot Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/PsychoTeleBot
Environment="PATH=/path/to/PsychoTeleBot/venv/bin"
ExecStart=/path/to/PsychoTeleBot/venv/bin/python -m adapters.telegram.run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активируйте сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable psychotelebot
sudo systemctl start psychotelebot
sudo systemctl status psychotelebot
```

Просмотр логов:
```bash
sudo journalctl -u psychotelebot -f
```

#### 3. Использовать screen/tmux

Альтернатива systemd:
```bash
# Создать screen сессию
screen -S psychobot

# Запустить бота
python -m adapters.telegram.run

# Отключиться: Ctrl+A, затем D
# Подключиться обратно:
screen -r psychobot
```

### Вариант B: Docker

#### 1. Создать Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "adapters.telegram.run"]
```

#### 2. Создать docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build: .
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./data:/app/data
```

#### 3. Запустить

```bash
docker-compose up -d
docker-compose logs -f
```

### Вариант C: Heroku

#### 1. Создать Procfile

```
worker: python -m adapters.telegram.run
```

#### 2. Создать runtime.txt

```
python-3.11.0
```

#### 3. Деплой

```bash
heroku login
heroku create psychotelebot
heroku config:set TELEGRAM_BOT_TOKEN=ваш_токен
git push heroku main
heroku ps:scale worker=1
heroku logs --tail
```

---

## 🔧 Дополнительные настройки

### Webhook вместо polling (опционально)

Для production рекомендуется использовать webhook:

```python
# В bot.py замените метод run():
def run_webhook(self, webhook_url: str, port: int = 8443):
    """Запуск бота с webhook"""
    self.application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=self.token,
        webhook_url=f"{webhook_url}/{self.token}"
    )
```

### Добавление БД (SQLite)

Создайте `infrastructure/sqlite_repositories.py`:

```python
import sqlite3
import json
from typing import Optional, List
from domain.models import UserSession, Ticket, State
from domain.repositories import SessionRepository, TicketRepository


class SQLiteSessionRepository(SessionRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id TEXT PRIMARY KEY,
                state TEXT,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    # Реализуйте методы get, save, delete
    # ...
```

Обновите `adapters/telegram/bot.py`:

```python
from infrastructure.sqlite_repositories import SQLiteSessionRepository

# В __init__:
session_repo = SQLiteSessionRepository("bot.db")
```

---

## 🐛 Решение проблем

### Бот не отвечает

1. Проверьте токен в `.env`
2. Проверьте логи: `journalctl -u psychotelebot -f`
3. Убедитесь, что бот запущен

### Ошибка "Invalid token"

Токен неверный. Проверьте:
1. Скопирован ли токен полностью
2. Нет ли лишних пробелов в `.env`
3. Перезапустите бота после изменения `.env`

### Бот падает при запуске

```bash
# Проверьте установку зависимостей
pip install -r requirements.txt --upgrade

# Проверьте версию Python
python --version  # должна быть 3.11+
```

---

## ✅ Чек-лист запуска

- [ ] Создан бот через @BotFather
- [ ] Получен и сохранен токен
- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Создан файл `.env` с токеном
- [ ] Создан адаптер `adapters/telegram/bot.py`
- [ ] Создан запускатель `adapters/telegram/run.py`
- [ ] Бот запущен (`python -m adapters.telegram.run`)
- [ ] Протестирован в Telegram (команда `/start`)

---

## 📚 Полезные ссылки

- [python-telegram-bot документация](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather команды](https://core.telegram.org/bots#botfather)

---

## 🎉 Готово!

Теперь ваш PsychoTeleBot работает в Telegram!

Для возврата к CLI режиму используйте:
```bash
python -m adapters.cli
```
