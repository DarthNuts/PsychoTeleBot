"""Telegram адаптер для PsychoTeleBot"""
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.sqlite_repositories import (
    SQLiteSessionRepository, 
    SQLiteTicketRepository, 
    SQLiteRoleRepository
)
from domain.roles import RoleManager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, db_path: str = "bot_data.db"):
        self.token = token
        self.db_path = db_path
        
        # Инициализируем репозитории с SQLite
        session_repo = SQLiteSessionRepository(db_path)
        ticket_repo = SQLiteTicketRepository(db_path)
        role_repo = SQLiteRoleRepository(db_path)
        
        # Получаем админов из переменных окружения
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = [aid.strip() for aid in admin_ids_str.split(",") if aid.strip()]
        
        # Инициализируем RoleManager с админами
        role_manager = RoleManager(admin_ids=admin_ids)
        
        # Загружаем существующие роли из БД
        for user_profile in role_repo.get_all_users():
            role_manager.users[user_profile.user_id] = user_profile
        
        state_machine = StateMachine()
        self.bot_service = BotService(
            session_repo, 
            ticket_repo, 
            state_machine,
            role_manager
        )
        self.role_repo = role_repo
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
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        
        response = self.bot_service.process_message(
            user_id, "/start", username, first_name, last_name
        )
        await update.message.reply_text(response, parse_mode="Markdown")
        logger.info(f"User {user_id} ({username}) started the bot")

    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/menu")
        await update.message.reply_text(response, parse_mode="Markdown")

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/clear")
        await update.message.reply_text(response, parse_mode="Markdown")

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
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        message = update.message.text
        
        logger.info(f"User {user_id} ({username}): {message}")
        
        response = self.bot_service.process_message(
            user_id, message, username, first_name, last_name
        )
        await update.message.reply_text(response, parse_mode="Markdown")
