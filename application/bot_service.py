from typing import Optional
from datetime import datetime
import uuid

from domain.models import UserSession, Ticket, State, TicketStatus
from domain.repositories import SessionRepository, TicketRepository
from application.state_machine import StateMachine


class BotService:
    """Основной сервис бота, координирующий все операции"""

    def __init__(
        self,
        session_repo: SessionRepository,
        ticket_repo: TicketRepository,
        state_machine: StateMachine
    ):
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.state_machine = state_machine

    def process_message(self, user_id: str, message: str) -> str:
        """
        Обработка сообщения от пользователя
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            
        Returns:
            str: Ответ бота
        """
        # Получаем или создаем сессию
        session = self.session_repo.get(user_id)
        if session is None:
            session = UserSession(user_id=user_id, state=State.MENU)
            self.session_repo.save(session)

        # Запоминаем предыдущее состояние
        previous_state = session.state
        
        # Обрабатываем сообщение через state machine
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
