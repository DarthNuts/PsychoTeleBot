# 🚀 Быстрое подключение к Telegram (5 минут)

## Шаг 1: Создать бота (2 минуты)

1. Откройте Telegram и найдите **@BotFather**
2. Отправьте `/newbot`
3. Введите имя: `PsychoTeleBot`
4. Введите username: `psycho_support_bot` (или любой свободный)
5. **Скопируйте токен** (выглядит так: `1234567890:ABCdef...`)

## Шаг 2: Установить зависимости (1 минута)

```bash
pip install -r requirements-telegram.txt
```

## Шаг 3: Настроить токен (30 секунд)

Создайте файл `.env` в корне проекта:
```bash
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
```

**Windows:**
```cmd
echo TELEGRAM_BOT_TOKEN=ваш_токен > .env
```

**Linux/Mac:**
```bash
echo "TELEGRAM_BOT_TOKEN=ваш_токен" > .env
```

## Шаг 4: Создать адаптер (1 минута)

Скопируйте готовый код:

**Создайте файл `adapters/telegram/__init__.py`:**
```python
# Telegram adapter
```

**Создайте файл `adapters/telegram/bot.py`:**

<details>
<summary>📄 Нажмите, чтобы показать код (скопируйте полностью)</summary>

```python
"""Telegram адаптер для PsychoTeleBot"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.in_memory_repositories import InMemorySessionRepository, InMemoryTicketRepository

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        session_repo = InMemorySessionRepository()
        ticket_repo = InMemoryTicketRepository()
        state_machine = StateMachine()
        self.bot_service = BotService(session_repo, ticket_repo, state_machine)
        self.application = Application.builder().token(token).build()
        self._register_handlers()

    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("menu", self.handle_menu))
        self.application.add_handler(CommandHandler("clear", self.handle_clear))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/start")
        await update.message.reply_text(response)
        logger.info(f"User {user_id} started the bot")

    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/menu")
        await update.message.reply_text(response)

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/clear")
        await update.message.reply_text(response)

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """🤖 *PsychoTeleBot - Помощь*

Доступные команды:
/start - Начать работу
/menu - Главное меню
/clear - Очистить контекст ИИ
/help - Показать справку"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        message = update.message.text
        logger.info(f"User {user_id}: {message}")
        response = self.bot_service.process_message(user_id, message)
        await update.message.reply_text(response)

    def run(self):
        logger.info("Starting PsychoTeleBot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
```
</details>

**Создайте файл `adapters/telegram/run.py`:**

```python
"""Точка входа для Telegram бота"""
import os
from dotenv import load_dotenv
from adapters.telegram.bot import TelegramBot

def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return
    bot = TelegramBot(token)
    bot.run()

if __name__ == "__main__":
    main()
```

## Шаг 5: Запустить! (30 секунд)

```bash
python -m adapters.telegram.run
```

Или используйте готовые скрипты:
- Windows: `run_telegram.bat`
- Linux/Mac: `./run_telegram.sh`

## ✅ Готово!

1. Откройте Telegram
2. Найдите вашего бота
3. Нажмите Start
4. Отправьте `/start`

Бот должен ответить приветствием! 🎉

---

## 🐛 Если что-то не работает

### "Invalid token"
- Проверьте токен в `.env`
- Убедитесь, что нет пробелов

### "Module not found"
```bash
pip install -r requirements-telegram.txt --upgrade
```

### Бот не отвечает
- Проверьте, что бот запущен (должна быть надпись "Starting PsychoTeleBot...")
- Проверьте интернет-соединение

---

## 📚 Дальнейшие шаги

- **Возможности бота**: [INSTRUCTIONS.md](INSTRUCTIONS.md)
- **Настройка ИИ**: [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md)
- **Настройка ролей**: [ROLES_SETUP.md](ROLES_SETUP.md)
- **Полная инструкция Telegram**: [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)
- **Деплой на сервер**: [TELEGRAM_SETUP.md#6-деплой](TELEGRAM_SETUP.md#6-деплой)

---

**Время выполнения:** ~5 минут  
**Сложность:** Легко ⭐  
**Результат:** Работающий бот в Telegram! 🤖
