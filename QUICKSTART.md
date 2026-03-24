# Быстрый старт PsychoTeleBot

## Требования

- Python 3.11+
- Telegram-аккаунт

---

## 1. Создайте бота в Telegram

1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`, задайте имя и username (должен заканчиваться на `bot`)
3. Скопируйте полученный **токен**

---

## 2. Установите зависимости

```bash
pip install -r requirements.txt
```

---

## 3. Настройте .env

Скопируйте шаблон и заполните:

```bash
cp .env.example .env
```

Откройте `.env` и укажите:

```env
# Обязательно: токен бота от @BotFather
TELEGRAM_BOT_TOKEN=ваш_токен

# Обязательно: ваш Telegram ID (для доступа к админ-панели)
# Узнать ID: отправьте /start боту @userinfobot
ADMIN_IDS=ваш_telegram_id

# Обязательно: ключ API OpenRouter (https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1-ваш_ключ

# Модель ИИ (по умолчанию бесплатная)
OPENROUTER_MODEL=arcee-ai/trinity-large-preview:free
```

---

## 4. Запустите бота

**Windows:**
```bash
.\run_telegram.bat
```

**Linux / Mac:**
```bash
python -m adapters.telegram.run
```

---

## 5. Проверьте работу

1. Найдите бота в Telegram по username
2. Отправьте `/start` — появится главное меню
3. Отправьте `/help` — справка по командам

---

## Что дальше

- **Добавить психолога** — зайдите в админ-панель (пункт «Управление психологами») и укажите Telegram ID специалиста
- **Полное описание возможностей** — [INSTRUCTIONS.md](INSTRUCTIONS.md)
- **Настройка ИИ (OpenRouter)** — [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md)
- **Настройка ролей** — [ROLES_SETUP.md](ROLES_SETUP.md)
- **Настройка Telegram-бота подробнее** — [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)
- **Запуск тестов** — `pytest -v`
