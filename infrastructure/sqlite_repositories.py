"""
SQLite хранилище для ролей и заявок
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List

from domain.models import UserSession, Ticket, TicketStatus
from domain.roles import UserProfile, UserRole
from domain.repositories import SessionRepository, TicketRepository


class SQLiteDatabase:
    """Базовый класс для работы с SQLite"""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализировать БД"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
    
    def get_connection(self):
        """Получить подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


class SQLiteSessionRepository(SessionRepository, SQLiteDatabase):
    """SQLite реализация репозитория сессий"""
    
    def _init_db(self):
        super()._init_db()
        conn = self.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                form_data TEXT,
                ai_context TEXT,
                current_ticket_id TEXT,
                pagination_offset INTEGER DEFAULT 0,
                selected_ticket_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Добавляем новые колонки если их нет (миграция для существующих БД)
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN pagination_offset INTEGER DEFAULT 0")
        except:
            pass
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN selected_ticket_id TEXT")
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def get(self, user_id: str) -> Optional[UserSession]:
        """Получить сессию"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Преобразуем row в dict для удобного доступа
        row_dict = dict(row)
        
        # Восстанавливаем объект UserSession
        from domain.models import ConsultationForm, State, Severity
        
        form_data = json.loads(row_dict['form_data']) if row_dict['form_data'] else {}
        ai_context = json.loads(row_dict['ai_context']) if row_dict['ai_context'] else []
        
        session = UserSession(user_id=user_id, state=State(row_dict['state']))
        
        # Восстанавливаем форму
        if form_data:
            # Преобразуем severity из строки в enum
            if form_data.get('severity') and isinstance(form_data['severity'], str):
                form_data['severity'] = Severity(form_data['severity'])
            session.consultation_form = ConsultationForm(**form_data)
        
        session.ai_context = ai_context
        session.current_ticket_id = row_dict.get('current_ticket_id')
        session.pagination_offset = row_dict.get('pagination_offset', 0) or 0
        session.selected_ticket_id = row_dict.get('selected_ticket_id')
        
        return session
    
    def save(self, session: UserSession) -> None:
        """Сохранить сессию"""
        conn = self.get_connection()
        
        form_data = {
            'topic': session.consultation_form.topic,
            'gender': session.consultation_form.gender,
            'age': session.consultation_form.age,
            'severity': session.consultation_form.severity.value if session.consultation_form.severity else None,
            'message': session.consultation_form.message,
        }
        
        conn.execute("""
            INSERT OR REPLACE INTO sessions 
            (user_id, state, form_data, ai_context, current_ticket_id, pagination_offset, selected_ticket_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.user_id,
            session.state.value,
            json.dumps(form_data),
            json.dumps(session.ai_context),
            session.current_ticket_id,
            session.pagination_offset,
            session.selected_ticket_id,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    
    def delete(self, user_id: str) -> None:
        """Удалить сессию"""
        conn = self.get_connection()
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()


class SQLiteTicketRepository(TicketRepository, SQLiteDatabase):
    """SQLite реализация репозитория заявок"""
    
    def _init_db(self):
        super()._init_db()
        conn = self.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                gender TEXT NOT NULL,
                age INTEGER NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                chat_history TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def create(self, ticket: Ticket) -> Ticket:
        """Создать заявку"""
        conn = self.get_connection()
        conn.execute("""
            INSERT INTO tickets 
            (id, user_id, topic, gender, age, severity, message, status, assigned_to, created_at, updated_at, chat_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket.id,
            ticket.user_id,
            ticket.topic,
            ticket.gender,
            ticket.age,
            ticket.severity.value,
            ticket.message,
            ticket.status.value,
            ticket.assigned_to,
            ticket.created_at.isoformat(),
            datetime.now().isoformat(),
            json.dumps(ticket.chat_history)
        ))
        conn.commit()
        conn.close()
        return ticket
    
    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Получить заявку"""
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_ticket(row)
    
    def get_all(self) -> List[Ticket]:
        """Получить все заявки"""
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_ticket(row) for row in rows]
    
    def get_by_user(self, user_id: str) -> List[Ticket]:
        """Получить заявки пользователя"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_ticket(row) for row in rows]
    
    def update(self, ticket: Ticket) -> None:
        """Обновить заявку"""
        conn = self.get_connection()
        conn.execute("""
            UPDATE tickets 
            SET status = ?, assigned_to = ?, updated_at = ?, chat_history = ?
            WHERE id = ?
        """, (
            ticket.status.value,
            ticket.assigned_to,
            datetime.now().isoformat(),
            json.dumps(ticket.chat_history),
            ticket.id
        ))
        conn.commit()
        conn.close()
    
    @staticmethod
    def _row_to_ticket(row) -> Ticket:
        """Преобразовать строку БД в объект Ticket"""
        from domain.models import Severity
        
        return Ticket(
            id=row['id'],
            user_id=row['user_id'],
            topic=row['topic'],
            gender=row['gender'],
            age=row['age'],
            severity=Severity(row['severity']),
            message=row['message'],
            status=TicketStatus(row['status']),
            assigned_to=row['assigned_to'],
            created_at=datetime.fromisoformat(row['created_at']),
            chat_history=json.loads(row['chat_history']) if row['chat_history'] else []
        )


class SQLiteRoleRepository:
    """SQLite хранилище для ролей"""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализировать таблицу ролей"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def get_or_create(self, user_id: str, username: str = None, 
                     first_name: str = None, last_name: str = None) -> UserProfile:
        """Получить или создать профиль"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM user_roles WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            # Создаем новый профиль
            conn.execute("""
                INSERT INTO user_roles 
                (user_id, role, username, first_name, last_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, UserRole.USER.value, username, first_name, last_name,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            conn.commit()
            profile = UserProfile(
                user_id=user_id,
                role=UserRole.USER,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
        else:
            profile = UserProfile(
                user_id=row[0],
                role=UserRole(row[1]),
                username=row[2],
                first_name=row[3],
                last_name=row[4],
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6])
            )
        
        conn.close()
        return profile
    
    def set_role(self, user_id: str, role: UserRole) -> None:
        """Установить роль пользователю"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE user_roles SET role = ?, updated_at = ? WHERE user_id = ?",
            (role.value, datetime.now().isoformat(), user_id)
        )
        conn.commit()
        conn.close()
    
    def save_user(self, profile: UserProfile) -> None:
        """Сохранить или обновить профиль пользователя"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO user_roles 
            (user_id, role, username, first_name, last_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.user_id,
            profile.role.value,
            profile.username,
            profile.first_name,
            profile.last_name,
            profile.created_at.isoformat(),
            profile.updated_at.isoformat()
        ))
        conn.commit()
        conn.close()
    
    def get_role(self, user_id: str) -> UserRole:
        """Получить роль пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role FROM user_roles WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserRole(row[0])
        return UserRole.USER
    
    def list_by_role(self, role: UserRole) -> List[UserProfile]:
        """Получить пользователей с определенной ролью"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM user_roles WHERE role = ?", (role.value,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [UserProfile(
            user_id=row[0],
            role=UserRole(row[1]),
            username=row[2],
            first_name=row[3],
            last_name=row[4],
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6])
        ) for row in rows]
    
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Получить профиль пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM user_roles WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return UserProfile(
            user_id=row[0],
            role=UserRole(row[1]),
            username=row[2],
            first_name=row[3],
            last_name=row[4],
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6])
        )
    
    def delete_user(self, user_id: str) -> None:
        """Удалить пользователя"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    
    def get_users_by_role(self, role: UserRole) -> List[UserProfile]:
        """Получить пользователей по роли (алиас для list_by_role)"""
        return self.list_by_role(role)
    
    def get_all_users(self) -> List[UserProfile]:
        """Получить всех пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM user_roles")
        rows = cursor.fetchall()
        conn.close()
        
        return [UserProfile(
            user_id=row[0],
            role=UserRole(row[1]),
            username=row[2],
            first_name=row[3],
            last_name=row[4],
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6])
        ) for row in rows]