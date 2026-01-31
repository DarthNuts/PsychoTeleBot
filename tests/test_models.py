import pytest
from domain.models import (
    State, UserSession, ConsultationForm, Ticket, 
    TicketStatus, Severity
)


def test_user_session_creation():
    """Тест создания пользовательской сессии"""
    session = UserSession(user_id="test_user")
    
    assert session.user_id == "test_user"
    assert session.state == State.MENU
    assert session.consultation_form is not None
    assert len(session.ai_context) == 0


def test_user_session_reset_form():
    """Тест сброса формы консультации"""
    session = UserSession(user_id="test_user")
    session.consultation_form.topic = "Test"
    session.consultation_form.age = 25
    
    session.reset_form()
    
    assert session.consultation_form.topic is None
    assert session.consultation_form.age is None


def test_user_session_clear_ai_context():
    """Тест очистки контекста ИИ"""
    session = UserSession(user_id="test_user")
    session.ai_context = [{"role": "user", "content": "test"}]
    
    session.clear_ai_context()
    
    assert len(session.ai_context) == 0


def test_user_session_go_to_menu():
    """Тест возврата в меню"""
    session = UserSession(user_id="test_user")
    session.state = State.CONSULT_FORM_AGE
    session.consultation_form.topic = "Test"
    
    session.go_to_menu()
    
    assert session.state == State.MENU
    assert session.consultation_form.topic is None


def test_consultation_form_is_complete():
    """Тест проверки заполненности формы"""
    form = ConsultationForm()
    
    assert not form.is_complete()
    
    form.topic = "Depression"
    form.gender = "Male"
    form.age = 30
    form.severity = Severity.MEDIUM
    form.message = "Help needed"
    
    assert form.is_complete()


def test_consultation_form_incomplete():
    """Тест незаполненной формы"""
    form = ConsultationForm()
    form.topic = "Test"
    form.gender = "Male"
    # Не заполнены age, severity, message
    
    assert not form.is_complete()


def test_ticket_creation():
    """Тест создания заявки"""
    ticket = Ticket(
        id="ticket_1",
        user_id="user_1",
        topic="Anxiety",
        gender="Female",
        age=28,
        severity=Severity.HIGH,
        message="Need help with anxiety"
    )
    
    assert ticket.id == "ticket_1"
    assert ticket.user_id == "user_1"
    assert ticket.status == TicketStatus.NEW
    assert ticket.assigned_to is None
    assert len(ticket.chat_history) == 0


def test_ticket_status_enum():
    """Тест enum статусов заявки"""
    assert TicketStatus.NEW.value == "Новое"
    assert TicketStatus.IN_PROGRESS.value == "В работе"
    assert TicketStatus.WAITING_RESPONSE.value == "Ожидание ответа"
    assert TicketStatus.CLOSED.value == "Закрыто"


def test_severity_enum():
    """Тест enum критичности"""
    assert Severity.LOW.value == "Низкая"
    assert Severity.MEDIUM.value == "Средняя"
    assert Severity.HIGH.value == "Высокая"
    assert Severity.CRITICAL.value == "Критическая"


def test_state_enum():
    """Тест enum состояний"""
    assert State.MENU == "MENU"
    assert State.CONSULT_FORM_TOPIC == "CONSULT_FORM_TOPIC"
    assert State.AI_CHAT == "AI_CHAT"
