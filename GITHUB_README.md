# 🤖 PsychoTeleBot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-32%20passed-success)](tests/)
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

🎯 **Начните здесь:** [START_HERE.md](START_HERE.md)

| Документ | Описание |
|----------|----------|
| **[TELEGRAM_QUICK.md](TELEGRAM_QUICK.md)** | Запуск в Telegram за 5 минут |
| **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** | Полная инструкция + деплой |
| **[QUICKSTART.md](QUICKSTART.md)** | Быстрый старт и примеры |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Архитектура проекта |
| **[DOCS_INDEX.md](DOCS_INDEX.md)** | Полный индекс документов |

---

## 🎯 Возможности

- ✅ **Консультация со специалистом** — форма с заявкой
- ✅ **ИИ-консультант** — чат с контекстом
- ✅ **Вопросы по психологии**
- ✅ **Анонимность**
- ✅ **Управление заявками**
- ✅ **Офлайн-отладка** без Telegram API

---

## 🏗️ Архитектура

```
PsychoTeleBot/
├── domain/           # Бизнес-логика
├── application/      # Use cases
├── infrastructure/   # Репозитории
├── adapters/         # CLI & Telegram
└── tests/           # 32 теста (100%)
```

**Clean Architecture** → Полная независимость от фреймворков

---

## 🧪 Тесты

```bash
pytest -v
# 32 passed in 0.11s ✅
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
