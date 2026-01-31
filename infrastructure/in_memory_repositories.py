from typing import Optional, Dict, List
from domain.models import UserSession, Ticket
from domain.repositories import SessionRepository, TicketRepository


class InMemorySessionRepository(SessionRepository):
    """In-memory реализация репозитория сессий"""

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}

    def get(self, user_id: str) -> Optional[UserSession]:
        """Получить сессию пользователя"""
        return self._sessions.get(user_id)

    def save(self, session: UserSession) -> None:
        """Сохранить сессию пользователя"""
        self._sessions[session.user_id] = session

    def delete(self, user_id: str) -> None:
        """Удалить сессию пользователя"""
        if user_id in self._sessions:
            del self._sessions[user_id]

    def clear_all(self):
        """Очистить все сессии (для тестов)"""
        self._sessions.clear()


class InMemoryTicketRepository(TicketRepository):
    """In-memory реализация репозитория заявок"""

    def __init__(self):
        self._tickets: Dict[str, Ticket] = {}

    def create(self, ticket: Ticket) -> Ticket:
        """Создать новую заявку"""
        self._tickets[ticket.id] = ticket
        return ticket

    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Получить заявку по ID"""
        return self._tickets.get(ticket_id)

    def get_all(self) -> List[Ticket]:
        """Получить все заявки"""
        return list(self._tickets.values())

    def update(self, ticket: Ticket) -> None:
        """Обновить заявку"""
        if ticket.id in self._tickets:
            self._tickets[ticket.id] = ticket

    def get_by_user(self, user_id: str) -> List[Ticket]:
        """Получить все заявки пользователя"""
        return [t for t in self._tickets.values() if t.user_id == user_id]

    def clear_all(self):
        """Очистить все заявки (для тестов)"""
        self._tickets.clear()
