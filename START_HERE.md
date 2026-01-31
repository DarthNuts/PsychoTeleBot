# 🚀 НАЧНИТЕ ЗДЕСЬ

## Выберите ваш путь:

### 1️⃣ Хочу запустить Telegram бота прямо сейчас (5 минут)
→ **[TELEGRAM_QUICK.md](TELEGRAM_QUICK.md)**

### 2️⃣ Хочу изучить проект и попробовать CLI
→ **[QUICKSTART.md](QUICKSTART.md)**

### 3️⃣ Нужна полная документация
→ **[DOCS_INDEX.md](DOCS_INDEX.md)** - индекс всех документов

### 4️⃣ Хочу подробную инструкцию по Telegram
→ **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)**

---

## 📚 Все документы

| Файл | Описание | Для кого |
|------|----------|----------|
| [TELEGRAM_QUICK.md](TELEGRAM_QUICK.md) | Запуск в Telegram за 5 минут | Все |
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | Полная инструкция по Telegram | Production деплой |
| [README.md](README.md) | Основная документация | Все |
| [QUICKSTART.md](QUICKSTART.md) | Быстрый старт | Новички |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура проекта | Разработчики |
| [CHEATSHEET.md](CHEATSHEET.md) | Шпаргалка команд | Все |
| [DOCS_INDEX.md](DOCS_INDEX.md) | Индекс документации | Навигация |
| [COMPLETION_REPORT.md](COMPLETION_REPORT.md) | Отчет о выполнении | Менеджеры |

---

## ⚡ Самые частые задачи

### Запустить в Telegram
```bash
pip install -r requirements-telegram.txt
echo "TELEGRAM_BOT_TOKEN=ваш_токен" > .env
python -m adapters.telegram.run
```

### Запустить CLI для тестирования
```bash
pip install -r requirements.txt
python -m adapters.cli
```

### Запустить тесты
```bash
pytest -v
```

---

**Время чтения:** 1 минута  
**Начните с:** [TELEGRAM_QUICK.md](TELEGRAM_QUICK.md) или [QUICKSTART.md](QUICKSTART.md)
