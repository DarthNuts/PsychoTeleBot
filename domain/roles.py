"""
Система ролей пользователей
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    USER = "user"
    PSYCHOLOGIST = "psychologist"
    ADMIN = "admin"


@dataclass
class UserProfile:
    """Профиль пользователя с ролью"""
    user_id: str
    role: UserRole = UserRole.USER
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class RoleManager:
    """Управление ролями пользователей в памяти"""
    
    def __init__(self, admin_ids: list[str] = None):
        """
        Инициализация
        
        Args:
            admin_ids: ID пользователей, которые будут администраторами
        """
        self.users: Dict[str, UserProfile] = {}
        self.admin_ids = set(admin_ids or [])
        # Не создаем профили автоматически - только при первом взаимодействии
    
    def get_or_create_user(self, user_id: str, username: str = None, 
                          first_name: str = None, last_name: str = None) -> UserProfile:
        """Получить или создать профиль пользователя"""
        if user_id not in self.users:
            # Новый пользователь
            role = UserRole.ADMIN if user_id in self.admin_ids else UserRole.USER
            self.users[user_id] = UserProfile(
                user_id=user_id,
                role=role,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
        
        # НЕ обновляем метаданные существующего пользователя
        return self.users[user_id]
    
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Получить профиль пользователя"""
        return self.users.get(user_id)
    
    def get_role(self, user_id: str) -> UserRole:
        """Получить роль пользователя"""
        if user_id in self.users:
            return self.users[user_id].role
        return UserRole.USER
    
    def promote_to_psychologist(self, user_id: str) -> bool:
        """Повысить до психолога"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        if user.role in (UserRole.ADMIN, UserRole.PSYCHOLOGIST):
            return False  # Уже имеет нужную роль
        
        user.role = UserRole.PSYCHOLOGIST
        user.updated_at = datetime.now()
        return True
    
    def demote_psychologist(self, user_id: str) -> bool:
        """Понизить психолога до пользователя"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        if user.role != UserRole.PSYCHOLOGIST:
            return False  # Не психолог
        
        user.role = UserRole.USER
        user.updated_at = datetime.now()
        return True
    
    def is_psychologist(self, user_id: str) -> bool:
        """Является ли пользователь психологом (не админом)"""
        role = self.get_role(user_id)
        return role == UserRole.PSYCHOLOGIST
    
    def is_admin(self, user_id: str) -> bool:
        """Является ли пользователь администратором"""
        # Проверяем admin_ids напрямую (даже если профиль не создан)
        if user_id in self.admin_ids:
            return True
        return self.get_role(user_id) == UserRole.ADMIN
    
    def list_psychologists(self) -> list[UserProfile]:
        """Получить список психологов (без админов)"""
        return [u for u in self.users.values() 
                if u.role == UserRole.PSYCHOLOGIST]
    
    def list_admins(self) -> list[UserProfile]:
        """Получить список администраторов"""
        return [u for u in self.users.values() if u.role == UserRole.ADMIN]
    
    def all_users(self) -> list[UserProfile]:
        """Получить всех пользователей"""
        return list(self.users.values())
