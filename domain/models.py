from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class State(str, Enum):
    """Состояния пользователя в боте"""
    MENU = "MENU"
    CONSULT_FORM_TOPIC = "CONSULT_FORM_TOPIC"
    CONSULT_FORM_GENDER = "CONSULT_FORM_GENDER"
    CONSULT_FORM_AGE = "CONSULT_FORM_AGE"
    CONSULT_FORM_SEVERITY = "CONSULT_FORM_SEVERITY"
    CONSULT_FORM_MESSAGE = "CONSULT_FORM_MESSAGE"
    AI_CHAT = "AI_CHAT"
    TERMS = "TERMS"
    PSY_QUESTION = "PSY_QUESTION"


class TicketStatus(str, Enum):
    """Статус заявки"""
    NEW = "Новое"
    IN_PROGRESS = "В работе"
    WAITING_RESPONSE = "Ожидание ответа"
    CLOSED = "Закрыто"


class Severity(str, Enum):
    """Критичность заявки"""
    LOW = "Низкая"
    MEDIUM = "Средняя"
    HIGH = "Высокая"
    CRITICAL = "Критическая"


@dataclass
class ConsultationForm:
    """Форма для консультации со специалистом"""
    topic: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    severity: Optional[Severity] = None
    message: Optional[str] = None

    def is_complete(self) -> bool:
        """Проверка, что форма заполнена полностью"""
        return all([
            self.topic,
            self.gender,
            self.age,
            self.severity,
            self.message
        ])


@dataclass
class Ticket:
    """Заявка на консультацию"""
    id: str
    user_id: str
    topic: str
    gender: str
    age: int
    severity: Severity
    message: str
    status: TicketStatus = TicketStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    chat_history: list[dict] = field(default_factory=list)


@dataclass
class UserSession:
    """Сессия пользователя"""
    user_id: str
    state: State = State.MENU
    consultation_form: ConsultationForm = field(default_factory=ConsultationForm)
    ai_context: list[dict] = field(default_factory=list)
    current_ticket_id: Optional[str] = None

    def reset_form(self):
        """Сброс формы консультации"""
        self.consultation_form = ConsultationForm()

    def clear_ai_context(self):
        """Очистка контекста ИИ"""
        self.ai_context = []

    def go_to_menu(self):
        """Возврат в меню"""
        self.state = State.MENU
        self.reset_form()
