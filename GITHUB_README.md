# 🤖 PsychoTeleBot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-171%20passed-success)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Telegram-бот для психологической поддержки** с офлайн-отладкой на основе Clean Architecture.

---

## ⚡ Быстрый старт

### Telegram (за 5 минут)
```bash
pip install -r requirements-telegram.txt
echo "TELEGRAM_BOT_TOKEN=ваш_токен" > .env
python -m adapters.telegram.run
```
📖 **[Подробная инструкция →](TELEGRAM_QUICK.md)**

### CLI отладка
```bash
pip install -r requirements.txt
python -m adapters.cli
```

---

## 📚 Документация

🎯 **Начните здесь:** [QUICKSTART.md](QUICKSTART.md)

| Документ | Описание |
|----------|----------|
| **[QUICKSTART.md](QUICKSTART.md)** | Быстрый старт |
| **[INSTRUCTIONS.md](INSTRUCTIONS.md)** | Полное описание возможностей |
| **[OPENROUTER_SETUP.md](OPENROUTER_SETUP.md)** | Настройка ИИ (OpenRouter) |
| **[ROLES_SETUP.md](ROLES_SETUP.md)** | Настройка ролей |
| **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** | Полная инструкция Telegram + деплой |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Архитектура проекта |
| **[DOCS_INDEX.md](DOCS_INDEX.md)** | Полный индекс документов |

---

## 🎯 Возможности

- ✅ **Консультация со специалистом** — форма с заявкой
- ✅ **ИИ-консультант** — чат с контекстом (OpenRouter)
- ✅ **Чат психолог–пользователь** — двусторонний чат через бота
- ✅ **Роли** — пользователь, психолог, администратор
- ✅ **Управление заявками** с пагинацией
- ✅ **SQLite хранилище** — сохранение между перезапусками
- ✅ **Офлайн-отладка** без Telegram API

---

## 🏗️ Архитектура

```
PsychoTeleBot/
├── domain/           # Бизнес-логика
├── application/      # Use cases + AI Service
├── infrastructure/   # SQLite + In-Memory репозитории
├── adapters/         # CLI & Telegram
└── tests/            # 171 тест (100%)
```

**Clean Architecture** → Полная независимость от фреймворков

---

## 🧪 Тесты

```bash
pytest -v
# 171 passed ✅
```

---

## 🚀 Деплой

- 🐳 **Docker** → [Инструкция](TELEGRAM_SETUP.md#вариант-b-docker)
- 📦 **Heroku** → [Инструкция](TELEGRAM_SETUP.md#вариант-c-heroku)
- 🖥️ **Linux (systemd)** → [Инструкция](TELEGRAM_SETUP.md#вариант-a-запуск-на-сервере-linux)

---

## 📄 Лицензия

MIT License - используйте свободно!

---

## 🤝 Вклад

Pull requests приветствуются!

1. Fork проекта
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request

---

## 📞 Поддержка

- 📖 [Документация](DOCS_INDEX.md)
- 🐛 [Issues](https://github.com/DarthNuts/PsychoTeleBot/issues)
- 💬 [Discussions](https://github.com/DarthNuts/PsychoTeleBot/discussions)

---

**Сделано с ❤️ для помощи людям**
