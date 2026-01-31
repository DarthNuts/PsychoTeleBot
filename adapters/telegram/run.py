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
