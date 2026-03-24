# 🚀 НАЧНИТЕ ЗДЕСЬ

## Выберите ваш путь:

### 1️⃣ Хочу запустить бота
→ **[QUICKSTART.md](QUICKSTART.md)**

### 2️⃣ Хочу узнать все возможности бота
→ **[INSTRUCTIONS.md](INSTRUCTIONS.md)**

### 3️⃣ Хочу настроить ИИ (OpenRouter)
→ **[OPENROUTER_SETUP.md](OPENROUTER_SETUP.md)**

### 4️⃣ Нужна полная документация
→ **[DOCS_INDEX.md](DOCS_INDEX.md)** - индекс всех документов

### 5️⃣ Хочу подробную инструкцию по Telegram
→ **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)**

---

## 📚 Все документы

| Файл | Описание | Для кого |
|------|----------|----------|
| [QUICKSTART.md](QUICKSTART.md) | Быстрый старт | Все |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | Полное описание возможностей | Все |
| [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) | Получение API-ключа ИИ | Настройка |
| [ROLES_SETUP.md](ROLES_SETUP.md) | Настройка ролей | Админы |
| [TELEGRAM_QUICK.md](TELEGRAM_QUICK.md) | Запуск в Telegram за 5 минут | Все |
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | Полная инструкция по Telegram | Production деплой |
| [README.md](README.md) | Основная документация | Разработчики |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура проекта | Разработчики |
| [CHEATSHEET.md](CHEATSHEET.md) | Шпаргалка команд | Все |
| [DOCS_INDEX.md](DOCS_INDEX.md) | Индекс документации | Навигация |

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
**Начните с:** [QUICKSTART.md](QUICKSTART.md) или [INSTRUCTIONS.md](INSTRUCTIONS.md)
