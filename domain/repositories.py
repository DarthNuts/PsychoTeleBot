from abc import ABC, abstractmethod
from typing import Optional, List
from .models import UserSession, Ticket
from .roles import UserProfile, UserRole


class SessionRepository(ABC):
    """Интерфейс репозитория для сессий пользователей"""
    
    @abstractmethod
    def get(self, user_id: str) -> Optional[UserSession]:
        """Получить сессию пользователя"""
        pass
    
    @abstractmethod
    def save(self, session: UserSession) -> None:
        """Сохранить сессию пользователя"""
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> None:
        """Удалить сессию пользователя"""
        pass


class TicketRepository(ABC):
    """Интерфейс репозитория для заявок"""
    
    @abstractmethod
    def create(self, ticket: Ticket) -> Ticket:
        """Создать новую заявку"""
        pass
    
    @abstractmethod
    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Получить заявку по ID"""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Ticket]:
        """Получить все заявки"""
        pass
    
    @abstractmethod
    def update(self, ticket: Ticket) -> None:
        """Обновить заявку"""
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[Ticket]:
        """Получить все заявки пользователя"""
        pass


class RoleRepository(ABC):
    """Интерфейс репозитория для ролей пользователей"""
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Получить профиль пользователя"""
        pass
    
    @abstractmethod
    def save_user(self, profile: UserProfile) -> None:
        """Сохранить профиль пользователя"""
        pass
    
    @abstractmethod
    def get_all_users(self) -> List[UserProfile]:
        """Получить всех пользователей"""
        pass
    
    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Удалить пользователя"""
        pass
    
    @abstractmethod
    def get_users_by_role(self, role: UserRole) -> List[UserProfile]:
        """Получить пользователей по роли"""
        pass
