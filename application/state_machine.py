from typing import Tuple
from domain.models import State, UserSession, Severity
from application.ai_service import generate_ai_reply, clear_user_memory, clear_user_rate_state
import logging

logger = logging.getLogger(__name__)


class StateMachine:
    """State Machine для управления состояниями пользователя"""

    MENU_TEXT = """
🏠 Главное меню

Выберите действие:
1️⃣ Консультация со специалистом
2️⃣ Консультация с ИИ
3️⃣ Условия обращения
4️⃣ Вопрос по психологии

Для возврата в меню в любой момент используйте команду /menu
"""

    WELCOME_TEXT = """
👋 Добро пожаловать в PsychoTeleBot!

Я помогу вам получить психологическую поддержку.
"""

    TERMS_TEXT = """
📋 Условия обращения и политика конфиденциальности

1. Все консультации анонимны
2. Ваши данные защищены
3. Чаты сохраняются только для истории консультации
4. Вы можете в любой момент прекратить консультацию

Для возврата в меню используйте /menu
"""

    AI_CHAT_TEXT = """
🤖 Консультация с ИИ-ассистентом

Вы можете задать любой вопрос. ИИ постарается помочь вам.

Команды:
/clear - очистить контекст диалога
/menu - вернуться в главное меню
"""

    PSY_QUESTION_TEXT = """
❓ Вопрос по психологии

Задайте свой вопрос, и мы постараемся на него ответить.

Для возврата в меню используйте /menu
"""

    def __init__(self):
        self.handlers = {
            State.MENU: self._handle_menu,
            State.CONSULT_FORM_TOPIC: self._handle_topic,
            State.CONSULT_FORM_GENDER: self._handle_gender,
            State.CONSULT_FORM_AGE: self._handle_age,
            State.CONSULT_FORM_SEVERITY: self._handle_severity,
            State.CONSULT_FORM_MESSAGE: self._handle_message,
            State.AI_CHAT: self._handle_ai_chat,
            State.TERMS: self._handle_terms,
            State.PSY_QUESTION: self._handle_psy_question,
        }

    def process(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """
        Обработка сообщения пользователя
        
        Returns:
            Tuple[UserSession, str]: Обновленная сессия и ответ бота
        """
        # Глобальные команды
        if message.strip().lower() in ['/menu', 'menu']:
            session.go_to_menu()
            return session, self.MENU_TEXT

        if message.strip().lower() in ['/clear', 'clear'] and session.state == State.AI_CHAT:
            session.clear_ai_context()
            clear_user_memory(session.user_id)
            clear_user_rate_state(session.user_id)
            return session, "🗑️ Контекст диалога очищен.\n\n" + self.AI_CHAT_TEXT

        # Приветствие при старте
        if message.strip().lower() in ['/start', 'start'] and session.state == State.MENU:
            return session, self.WELCOME_TEXT + self.MENU_TEXT

        # Обработка по текущему состоянию
        handler = self.handlers.get(session.state)
        if handler:
            return handler(session, message)
        
        return session, "Неизвестная команда. Используйте /menu для возврата в главное меню."

    def _handle_menu(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка главного меню"""
        message_lower = message.strip().lower()
        
        if message_lower in ['1', 'консультация со специалистом']:
            session.state = State.CONSULT_FORM_TOPIC
            return session, "📝 Консультация со специалистом\n\nУкажите тему консультации:"
        
        elif message_lower in ['2', 'консультация с ии', 'консультация с ии']:
            session.state = State.AI_CHAT
            return session, self.AI_CHAT_TEXT
        
        elif message_lower in ['3', 'условия обращения']:
            session.state = State.TERMS
            return session, self.TERMS_TEXT
        
        elif message_lower in ['4', 'вопрос по психологии']:
            session.state = State.PSY_QUESTION
            return session, self.PSY_QUESTION_TEXT
        
        else:
            return session, self.MENU_TEXT

    def _handle_topic(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка ввода темы консультации"""
        session.consultation_form.topic = message
        session.state = State.CONSULT_FORM_GENDER
        return session, "Укажите ваш пол:"

    def _handle_gender(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка ввода пола"""
        session.consultation_form.gender = message
        session.state = State.CONSULT_FORM_AGE
        return session, "Укажите ваш возраст:"

    def _handle_age(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка ввода возраста"""
        try:
            age = int(message)
            if age < 1 or age > 120:
                return session, "Пожалуйста, укажите корректный возраст (от 1 до 120):"
            
            session.consultation_form.age = age
            session.state = State.CONSULT_FORM_SEVERITY
            return session, """Укажите критичность вашего обращения:
1. Низкая
2. Средняя
3. Высокая
4. Критическая"""
        except ValueError:
            return session, "Пожалуйста, введите число (ваш возраст):"

    def _handle_severity(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка ввода критичности"""
        severity_map = {
            '1': Severity.LOW,
            'низкая': Severity.LOW,
            '2': Severity.MEDIUM,
            'средняя': Severity.MEDIUM,
            '3': Severity.HIGH,
            'высокая': Severity.HIGH,
            '4': Severity.CRITICAL,
            'критическая': Severity.CRITICAL,
        }
        
        severity = severity_map.get(message.strip().lower())
        if severity:
            session.consultation_form.severity = severity
            session.state = State.CONSULT_FORM_MESSAGE
            return session, "Опишите вашу ситуацию подробно:"
        else:
            return session, "Пожалуйста, выберите критичность (1-4 или название):"

    def _handle_message(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка финального сообщения и создания заявки"""
        session.consultation_form.message = message
        
        # Заявка будет создана через use case
        # Здесь просто переходим в меню
        session.state = State.MENU
        
        response = "✅ Заявка создана! Специалист свяжется с вами в ближайшее время.\n\n"
        response += self.MENU_TEXT
        
        return session, response

    def _handle_ai_chat(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка чата с ИИ"""
        # Добавляем сообщение пользователя в контекст
        session.ai_context.append({"role": "user", "content": message})
        
        try:
            # Генерируем ответ через AI API
            ai_response = generate_ai_reply(
                user_id=session.user_id,
                user_message=message,
                history=session.ai_context[:-1]  # Передаем историю без последнего сообщения
            )
            
            # Добавляем ответ AI в контекст
            session.ai_context.append({"role": "assistant", "content": ai_response})
            
            # Ограничиваем историю последними 20 сообщениями (10 пар)
            if len(session.ai_context) > 20:
                session.ai_context = session.ai_context[-20:]
            
            return session, ai_response
            
        except Exception as e:
            logger.error(f"Error in AI chat handler: {type(e).__name__} - {str(e)[:100]}")
            fallback = "Извините, произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз."
            session.ai_context.append({"role": "assistant", "content": fallback})
            return session, fallback

    def _handle_terms(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка экрана условий"""
        # Любое сообщение возвращает в меню
        session.state = State.MENU
        return session, self.MENU_TEXT

    def _handle_psy_question(self, session: UserSession, message: str) -> Tuple[UserSession, str]:
        """Обработка вопроса по психологии (заглушка)"""
        response = f"❓ Ваш вопрос: {message}\n\n"
        response += "Спасибо за вопрос! Специалист ответит на него в ближайшее время.\n\n"
        
        session.state = State.MENU
        response += self.MENU_TEXT
        
        return session, response
