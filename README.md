# PsychoTeleBot

Telegram-бот для психологической поддержки с офлайн-отладкой (Clean Architecture).

📚 **[Полный индекс документации →](DOCS_INDEX.md)** | **[Быстрый старт →](QUICKSTART.md)** | **[Возможности бота →](INSTRUCTIONS.md)**

---

## Описание

PsychoTeleBot — это бот для Telegram, предназначенный для предоставления психологической поддержки. Реализован с использованием принципов Clean Architecture, что позволяет полностью тестировать бизнес-логику **без использования Telegram API**.

## Возможности

- 🏠 **Главное меню** с выбором действий
- 👨‍⚕️ **Консультация со специалистом** — создание заявки с полной формой
- 💬 **Чат психолог–пользователь** — двусторонний чат через бота
- 🤖 **Консультация с ИИ** — чат с ИИ-ассистентом (OpenRouter)
- 📋 **Условия обращения** — отображение политики конфиденциальности
- ❓ **Вопрос по психологии** — быстрые вопросы
- 🔄 **Команда /menu** — возврат в меню из любого состояния
- 🗑️ **Команда /clear** — очистка контекста ИИ-чата
- 👨‍⚕️ **Роль психолога** — управление заявками, чат с пользователями
- 🔧 **Роль администратора** — управление психологами, назначение заявок
- 💾 **SQLite хранилище** — данные сохраняются между перезапусками

📖 **Полное описание возможностей:** [INSTRUCTIONS.md](INSTRUCTIONS.md)

## Архитектура

Проект следует принципам Clean Architecture:

```
PsychoTeleBot/
├── domain/              # Бизнес-логика и модели
│   ├── models.py        # Доменные модели (State, Ticket, UserSession)
│   ├── repositories.py  # Интерфейсы репозиториев
│   └── roles.py         # Роли (UserRole)
├── application/         # Use cases и бизнес-процессы
│   ├── state_machine.py # State Machine для управления состояниями
│   ├── bot_service.py   # Основной сервис бота
│   └── ai_service.py    # Интеграция с OpenRouter (LLM)
├── infrastructure/      # Реализации репозиториев
│   ├── in_memory_repositories.py  # Для тестов
│   └── sqlite_repositories.py    # SQLite (production)
├── adapters/            # Адаптеры для внешнего мира
│   ├── cli/             # CLI адаптер для отладки
│   └── telegram/        # Telegram адаптер (production)
│       ├── bot.py       # Обработчики команд
│       └── run.py       # Точка запуска
└── tests/               # 171 тест (100%)
    ├── test_models.py
    ├── test_state_machine.py
    ├── test_bot_service.py
    ├── test_admin_commands.py
    ├── test_ai_service.py
    ├── test_roles.py
    └── test_ticket_assignment.py
```

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository_url>
cd PsychoTeleBot
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
```

3. Активируйте виртуальное окружение:
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- Linux/Mac:
  ```bash
  source venv/bin/activate
  ```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Использование

### Режим 1: Telegram Bot (production)

Для запуска бота в Telegram:

1. **Создайте бота через @BotFather** (см. [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md))
2. **Установите зависимости:**
   ```bash
   pip install -r requirements-telegram.txt
   ```
3. **Настройте токен в .env:**
   ```bash
   TELEGRAM_BOT_TOKEN=ваш_токен
   ```
4. **Запустите бота:**
   ```bash
   python -m adapters.telegram.run
   # или
   run_telegram.bat  # Windows
   ./run_telegram.sh # Linux/Mac
   ```

📖 **Подробная инструкция:** [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | **Настройка ИИ:** [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) | **Роли:** [ROLES_SETUP.md](ROLES_SETUP.md)

### Режим 2: CLI Debug Mode (офлайн-отладка)

Для тестирования бота без Telegram API используйте CLI:

```bash
python -m adapters.cli
```

Доступные команды CLI:
- `/start` — начать диалог
- `/menu` — вернуться в меню
- `/clear` — очистить контекст ИИ (в режиме AI_CHAT)
- `/reset` — сбросить сессию текущего пользователя
- `/user <id>` — сменить текущего пользователя
- `/tickets` — показать все заявки
- `/quit` — выход из CLI

### Пример использования CLI:

```
============================================================
  PsychoTeleBot - CLI Debug Mode
============================================================

Доступные команды:
  /start - начать диалог
  /menu - вернуться в меню
  /clear - очистить контекст ИИ
  /reset - сбросить сессию
  /user <id> - сменить пользователя
  /tickets - показать все заявки
  /quit - выход
============================================================

🤖 Бот:
👋 Добро пожаловать в PsychoTeleBot!

Я помогу вам получить психологическую поддержку.

🏠 Главное меню

Выберите действие:
1️⃣ Консультация со специалистом
2️⃣ Консультация с ИИ
3️⃣ Условия обращения
4️⃣ Вопрос по психологии

[test_user_1] > 1
```

## Запуск тестов

Для запуска всех тестов:

```bash
pytest
```

Для запуска с подробным выводом:

```bash
pytest -v
```

Для запуска конкретного теста:

```bash
pytest tests/test_bot_service.py::test_consultation_full_flow -v
```

## State Machine

Бот использует конечный автомат (State Machine) для управления состояниями:

### Состояния пользователя:
- `MENU` — главное меню
- `CONSULT_FORM_*` — форма заявки (5 шагов: тема, пол, возраст, критичность, сообщение)
- `AI_CHAT` — чат с ИИ
- `TERMS` — условия обращения
- `PSY_QUESTION` — вопрос по психологии
- `USER_IN_CHAT` — чат с психологом

### Состояния психолога:
- `PSY_MENU` — меню психолога
- `PSY_TICKETS_LIST` / `PSY_MY_TICKETS` — списки заявок
- `PSY_TICKET_OPEN` — просмотр заявки
- `PSY_TICKET_CHAT` — чат с пользователем
- `PSY_CHANGE_STATUS` — смена статуса

### Состояния админа:
- `ADMIN_MENU` — меню админа
- `ADMIN_MANAGE_PSYCHOLOGISTS` — управление психологами
- `ADMIN_PROMOTE_PSYCHO` / `ADMIN_DEMOTE_PSYCHO_SELECT` — назначение/снятие психологов
- `ADMIN_ASSIGN_TICKET_SELECT` / `ADMIN_ASSIGN_PSYCHO_SELECT` — назначение заявок

Всего: **27 состояний**. Полное описание: [INSTRUCTIONS.md](INSTRUCTIONS.md)

### Глобальные команды:
- `/menu` — возврат в меню из любого состояния
- `/clear` — очистка контекста ИИ
- `/end` — завершение чата психолог–пользователь

## Модели данных

### UserSession
Хранит состояние пользователя:
- `user_id` — ID пользователя
- `state` — текущее состояние
- `consultation_form` — данные формы консультации
- `ai_context` — контекст диалога с ИИ
- `current_ticket_id` — ID текущей заявки

### Ticket
Заявка на консультацию:
- `id` — уникальный ID
- `user_id` — ID пользователя
- `topic` — тема консультации
- `gender` — пол
- `age` — возраст
- `severity` — критичность (LOW, MEDIUM, HIGH, CRITICAL)
- `message` — сообщение
- `status` — статус (NEW, IN_PROGRESS, WAITING_RESPONSE, CLOSED)
- `assigned_to` — назначенный специалист
- `chat_history` — история чата

## Расширение

### ✅ Подключение к Telegram

**Уже реализовано!** Полная инструкция: [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)

Быстрый старт:
```bash
# 1. Установите зависимости
pip install -r requirements-telegram.txt

# 2. Создайте .env файл с токеном
echo "TELEGRAM_BOT_TOKEN=ваш_токен" > .env

# 3. Запустите бота
python -m adapters.telegram.run
```

Инструкция включает:
- Создание бота через @BotFather
- Полный код адаптера
- Деплой на сервер (Docker, Heroku, systemd)
- Решение проблем

### База данных

✅ **Реализовано!** SQLite-хранилище в `infrastructure/sqlite_repositories.py`.
Данные сохраняются в `bot_data.db` между перезапусками бота.

## Тестирование

Проект покрыт тестами:
- ✅ Unit-тесты моделей
- ✅ Unit-тесты State Machine
- ✅ Интеграционные тесты BotService
- ✅ End-to-end тесты пользовательских сценариев

Все тесты работают **офлайн**, без зависимостей от внешних сервисов.

## Лицензия

MIT

## Авторы

PsychoTeleBot Team
