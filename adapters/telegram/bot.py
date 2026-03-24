"""Telegram адаптер для PsychoTeleBot"""
import logging
import os
from telegram import Update, BotCommand
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.sqlite_repositories import (
    SQLiteSessionRepository, 
    SQLiteTicketRepository, 
    SQLiteRoleRepository
)
from domain.roles import RoleManager, UserRole

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
        
        # Загружаем существующие роли из БД и синхронизируем админов с .env
        for user_profile in role_repo.get_all_users():
            # Если пользователь был админом в БД, но его нет в ADMIN_IDS — снимаем админку
            if user_profile.role == UserRole.ADMIN and user_profile.user_id not in admin_ids:
                user_profile.role = UserRole.USER
                role_repo.save_user(user_profile)
            # Если пользователь в ADMIN_IDS, но роль не admin — повышаем
            elif user_profile.user_id in admin_ids and user_profile.role != UserRole.ADMIN:
                user_profile.role = UserRole.ADMIN
                role_repo.save_user(user_profile)

            role_manager.users[user_profile.user_id] = user_profile
        
        state_machine = StateMachine()
        self.bot_service = BotService(
            session_repo, 
            ticket_repo, 
            state_machine,
            role_manager,
            role_repo  # Передаем role_repo для сохранения профилей
        )
        self.role_repo = role_repo
        self.application = Application.builder().token(token).build()
        self._register_handlers()
        
        # Регистрируем команды для меню Telegram
        self.application.post_init = self._post_init

    async def _post_init(self, application: Application):
        """Устанавливаем команды бота после инициализации"""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("menu", "Главное меню"),
            BotCommand("clear", "Очистить контекст ИИ"),
            BotCommand("help", "Справка по командам"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Команды бота установлены")

    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("menu", self.handle_menu))
        self.application.add_handler(CommandHandler("clear", self.handle_clear))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("end", self.handle_end))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def _send_pending_notifications(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправить накопленные уведомления другим пользователям"""
        notifications = self.bot_service.get_pending_notifications()
        for target_user_id, text in notifications:
            try:
                await context.bot.send_message(
                    chat_id=int(target_user_id),
                    text=text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {target_user_id}: {e}")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        
        response = self.bot_service.process_message(
            user_id, "/start", username, first_name, last_name
        )
        await update.message.reply_text(response, parse_mode="Markdown")
        await self._send_pending_notifications(context)
        logger.info(f"User {user_id} ({username}) started the bot")

    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/menu")
        await update.message.reply_text(response, parse_mode="Markdown")
        await self._send_pending_notifications(context)

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/clear")
        await update.message.reply_text(response, parse_mode="Markdown")
        await self._send_pending_notifications(context)

    async def handle_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = self.bot_service.process_message(user_id, "/end")
        await update.message.reply_text(response, parse_mode="Markdown")
        await self._send_pending_notifications(context)

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

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        response = self.bot_service.process_message(
            user_id, message, username, first_name, last_name
        )
        await update.message.reply_text(response, parse_mode="Markdown")
        await self._send_pending_notifications(context)
    def run(self):
        logger.info("Starting PsychoTeleBot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)