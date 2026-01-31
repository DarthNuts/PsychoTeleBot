from typing import Optional
from datetime import datetime
import uuid

from domain.models import UserSession, Ticket, State, TicketStatus
from domain.repositories import SessionRepository, TicketRepository
from domain.roles import UserRole, RoleManager, UserProfile
from application.state_machine import StateMachine


class BotService:
    """Основной сервис бота, координирующий все операции"""

    def __init__(
        self,
        session_repo: SessionRepository,
        ticket_repo: TicketRepository,
        state_machine: StateMachine,
        role_manager: RoleManager = None
    ):
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.state_machine = state_machine
        self.role_manager = role_manager or RoleManager()

    def process_message(self, user_id: str, message: str, 
                       username: str = None, first_name: str = None, 
                       last_name: str = None) -> str:
        """
        Обработка сообщения от пользователя
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            username: Username пользователя (Telegram)
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            str: Ответ бота
        """
        # Получаем или создаем профиль пользователя
        user_profile = self.role_manager.get_or_create_user(
            user_id, username, first_name, last_name
        )
        
        # Получаем или создаем сессию
        session = self.session_repo.get(user_id)
        if session is None:
            session = UserSession(user_id=user_id, state=State.MENU)
            self.session_repo.save(session)

        # Запоминаем предыдущее состояние
        previous_state = session.state
        
        # Проверяем роль и выбираем обработчик
        if self.role_manager.is_admin(user_id):
            # Админ меню
            session, response = self._handle_admin_message(session, message, user_id)
        elif self.role_manager.is_psychologist(user_id):
            # Психолог меню
            session, response = self._handle_psychologist_message(session, message, user_id)
        else:
            # Обычный пользователь
            session, response = self.state_machine.process(session, message)
        
        # Если завершили форму консультации, создаем заявку
        if (previous_state == State.CONSULT_FORM_MESSAGE and 
            session.state == State.MENU and 
            session.consultation_form.is_complete()):
            
            ticket = self._create_ticket_from_form(session)
            session.current_ticket_id = ticket.id
            session.reset_form()
        
        # Сохраняем сессию
        self.session_repo.save(session)
        
        return response

    def _handle_admin_message(self, session: UserSession, message: str, user_id: str) -> tuple:
        """Обработка сообщений администратора"""
        message_lower = message.strip().lower()
        
        if session.state == State.MENU or message_lower in ['/start', 'start']:
            session.state = State.ADMIN_MENU
            response = """👑 *АДМИН-ПАНЕЛЬ*

Выберите действие:
1️⃣ Управление психологами
2️⃣ Все заявки
3️⃣ Назначить на заявку
4️⃣ Обычное меню

Команды:
/menu - вернуться в обычное меню"""
            return session, response
        
        elif session.state == State.ADMIN_MENU:
            if message_lower in ['1', 'управление психологами']:
                session.state = State.ADMIN_MANAGE_PSYCHOLOGISTS
                psychologists = self.role_manager.list_psychologists()
                
                if not psychologists:
                    response = "Психологи не назначены\n\nДля добавления отправьте ID пользователя:"
                else:
                    response = "👥 Текущие психологи:\n"
                    for psy in psychologists:
                        name = f"{psy.first_name or ''} {psy.last_name or ''}".strip()
                        response += f"\n• {psy.user_id} ({psy.username or name or 'нет имени'})"
                    response += "\n\nДля добавления нового отправьте ID пользователя:"
                
                return session, response
            
            elif message_lower in ['2', 'все заявки']:
                tickets = self.ticket_repo.get_all()
                if not tickets:
                    response = "📋 Заявок нет"
                else:
                    response = "📋 Все заявки:\n"
                    for t in tickets[-10:]:  # Последние 10
                        response += f"\n• {t.id[:8]} - {t.topic} ({t.status.value})"
                return session, response
            
            elif message_lower in ['4', 'обычное меню']:
                session.state = State.MENU
                return session, "Перешли в обычное меню"
        
        elif session.state == State.ADMIN_MANAGE_PSYCHOLOGISTS:
            if message_lower.isdigit():
                user_id_to_promote = message.strip()
                success = self.role_manager.promote_to_psychologist(user_id_to_promote)
                
                if success:
                    response = f"✅ Пользователь {user_id_to_promote} повышен до психолога"
                else:
                    response = f"❌ Не удалось повысить пользователя (возможно, уже психолог)"
                
                session.state = State.ADMIN_MENU
                return session, response
        
        return session, "❌ Неизвестная команда"

    def _handle_psychologist_message(self, session: UserSession, message: str, user_id: str) -> tuple:
        """Обработка сообщений психолога"""
        message_lower = message.strip().lower()
        
        if session.state == State.MENU or message_lower in ['/start', 'start']:
            session.state = State.PSY_MENU
            response = """🧑‍⚕️ *ПАНЕЛЬ ПСИХОЛОГА*

Выберите действие:
1️⃣ Очередь заявок
2️⃣ Мои заявки
3️⃣ Обычное меню

Команды:
/menu - вернуться в обычное меню"""
            return session, response
        
        elif session.state == State.PSY_MENU:
            if message_lower in ['1', 'очередь заявок']:
                session.state = State.PSY_TICKETS_LIST
                tickets = [t for t in self.ticket_repo.get_all() 
                          if t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE)]
                
                if not tickets:
                    response = "✅ Нет заявок в очереди"
                    session.state = State.PSY_MENU
                else:
                    response = "📋 Заявки:\n"
                    for i, t in enumerate(tickets[:5], 1):
                        response += f"\n{i}. {t.id[:8]} - {t.topic} ({t.severity.value})"
                        response += f"\n   От: {t.user_id}"
                
                return session, response
            
            elif message_lower in ['2', 'мои заявки']:
                tickets = [t for t in self.ticket_repo.get_all() 
                          if t.assigned_to == user_id]
                
                if not tickets:
                    response = "Вы не брали в работу ни одну заявку"
                else:
                    response = "📋 Ваши заявки:\n"
                    for t in tickets:
                        response += f"\n• {t.id[:8]} - {t.topic} ({t.status.value})"
                
                return session, response
            
            elif message_lower in ['3', 'обычное меню']:
                session.state = State.MENU
                return session, "Перешли в обычное меню"
        
        # Если психолог в обычной заявке - то же самое
        return self.state_machine.process(session, message)
    def _create_ticket_from_form(self, session: UserSession) -> Ticket:
        """Создание заявки из заполненной формы"""
        form = session.consultation_form
        
        ticket = Ticket(
            id=str(uuid.uuid4()),
            user_id=session.user_id,
            topic=form.topic,
            gender=form.gender,
            age=form.age,
            severity=form.severity,
            message=form.message,
            status=TicketStatus.NEW,
            created_at=datetime.now()
        )
        
        return self.ticket_repo.create(ticket)

    def get_user_tickets(self, user_id: str) -> list[Ticket]:
        """Получение всех заявок пользователя"""
        return self.ticket_repo.get_by_user(user_id)

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Получение заявки по ID"""
        return self.ticket_repo.get(ticket_id)

    def update_ticket_status(self, ticket_id: str, status: TicketStatus) -> bool:
        """Обновление статуса заявки"""
        ticket = self.ticket_repo.get(ticket_id)
        if ticket:
            ticket.status = status
            self.ticket_repo.update(ticket)
            return True
        return False

    def assign_ticket(self, ticket_id: str, specialist_id: str) -> bool:
        """Назначение заявки специалисту"""
        ticket = self.ticket_repo.get(ticket_id)
        if ticket:
            ticket.assigned_to = specialist_id
            ticket.status = TicketStatus.IN_PROGRESS
            self.ticket_repo.update(ticket)
            return True
        return False

    def get_all_tickets(self) -> list[Ticket]:
        """Получение всех заявок (для админов)"""
        return self.ticket_repo.get_all()

    def add_message_to_ticket(self, ticket_id: str, user_id: str, message: str) -> bool:
        """Добавление сообщения в чат заявки"""
        ticket = self.ticket_repo.get(ticket_id)
        if ticket:
            ticket.chat_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "message": message
            })
            self.ticket_repo.update(ticket)
            return True
        return False

    def get_user_role(self, user_id: str) -> UserRole:
        """Получить роль пользователя"""
        return self.role_manager.get_role(user_id)

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Получить профиль пользователя"""
        return self.role_manager.get_user(user_id)

    def promote_to_psychologist(self, user_id: str) -> bool:
        """Повысить до психолога"""
        return self.role_manager.promote_to_psychologist(user_id)

    def demote_psychologist(self, user_id: str) -> bool:
        """Понизить психолога"""
        return self.role_manager.demote_psychologist(user_id)

