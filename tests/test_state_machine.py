import pytest
from domain.models import State, UserSession, ConsultationForm, Severity
from application.state_machine import StateMachine


@pytest.fixture
def state_machine():
    """Фикстура для создания экземпляра StateMachine"""
    return StateMachine()


@pytest.fixture
def session():
    """Фикстура для создания тестовой сессии"""
    return UserSession(user_id="test_user")


def test_start_command(state_machine, session):
    """Тест команды /start"""
    session, response = state_machine.process(session, "/start")
    
    assert "Добро пожаловать" in response
    assert "Главное меню" in response
    assert session.state == State.MENU


def test_menu_selection_consultation(state_machine, session):
    """Тест выбора консультации со специалистом"""
    session.state = State.MENU
    
    session, response = state_machine.process(session, "1")
    
    assert session.state == State.CONSULT_FORM_TOPIC
    assert "тему консультации" in response


def test_menu_selection_ai(state_machine, session):
    """Тест выбора консультации с ИИ"""
    session.state = State.MENU
    
    session, response = state_machine.process(session, "2")
    
    assert session.state == State.AI_CHAT
    assert "ИИ-ассистентом" in response


def test_menu_command_from_any_state(state_machine, session):
    """Тест команды menu из любого состояния"""
    # Устанавливаем произвольное состояние
    session.state = State.CONSULT_FORM_AGE
    session.consultation_form.topic = "Test"
    
    session, response = state_machine.process(session, "/menu")
    
    assert session.state == State.MENU
    assert "Главное меню" in response
    # Проверяем, что форма сброшена
    assert session.consultation_form.topic is None


def test_clear_command_in_ai_chat(state_machine, session):
    """Тест команды clear в AI чате"""
    session.state = State.AI_CHAT
    session.ai_context = [{"role": "user", "content": "test"}]
    
    session, response = state_machine.process(session, "/clear")
    
    assert len(session.ai_context) == 0
    assert "очищен" in response


def test_consultation_form_flow(state_machine, session):
    """Тест полного потока заполнения формы консультации"""
    # Тема
    session.state = State.CONSULT_FORM_TOPIC
    session, response = state_machine.process(session, "Депрессия")
    assert session.state == State.CONSULT_FORM_GENDER
    assert session.consultation_form.topic == "Депрессия"
    
    # Пол
    session, response = state_machine.process(session, "Женский")
    assert session.state == State.CONSULT_FORM_AGE
    assert session.consultation_form.gender == "Женский"
    
    # Возраст
    session, response = state_machine.process(session, "25")
    assert session.state == State.CONSULT_FORM_SEVERITY
    assert session.consultation_form.age == 25
    
    # Критичность
    session, response = state_machine.process(session, "2")
    assert session.state == State.CONSULT_FORM_MESSAGE
    assert session.consultation_form.severity == Severity.MEDIUM
    
    # Сообщение
    session, response = state_machine.process(session, "Нужна помощь")
    assert session.state == State.MENU
    assert session.consultation_form.message == "Нужна помощь"
    assert "Заявка создана" in response


def test_age_validation(state_machine, session):
    """Тест валидации возраста"""
    session.state = State.CONSULT_FORM_AGE
    
    # Некорректный ввод (не число)
    session_new, response = state_machine.process(session, "abc")
    assert session_new.state == State.CONSULT_FORM_AGE
    assert "введите число" in response
    
    # Некорректный возраст (слишком большой)
    session_new, response = state_machine.process(session, "150")
    assert session_new.state == State.CONSULT_FORM_AGE
    assert "корректный возраст" in response
    
    # Корректный возраст
    session_new, response = state_machine.process(session, "30")
    assert session_new.state == State.CONSULT_FORM_SEVERITY


def test_severity_by_number(state_machine, session):
    """Тест выбора критичности по номеру"""
    session.state = State.CONSULT_FORM_SEVERITY
    
    test_cases = [
        ("1", Severity.LOW),
        ("2", Severity.MEDIUM),
        ("3", Severity.HIGH),
        ("4", Severity.CRITICAL),
    ]
    
    for input_val, expected_severity in test_cases:
        test_session = UserSession(user_id="test")
        test_session.state = State.CONSULT_FORM_SEVERITY
        
        test_session, response = state_machine.process(test_session, input_val)
        assert test_session.consultation_form.severity == expected_severity


def test_severity_by_name(state_machine, session):
    """Тест выбора критичности по названию"""
    session.state = State.CONSULT_FORM_SEVERITY
    
    test_cases = [
        ("низкая", Severity.LOW),
        ("средняя", Severity.MEDIUM),
        ("высокая", Severity.HIGH),
        ("критическая", Severity.CRITICAL),
    ]
    
    for input_val, expected_severity in test_cases:
        test_session = UserSession(user_id="test")
        test_session.state = State.CONSULT_FORM_SEVERITY
        
        test_session, response = state_machine.process(test_session, input_val)
        assert test_session.consultation_form.severity == expected_severity


def test_ai_chat_interaction(state_machine, session):
    """Тест взаимодействия с ИИ чатом"""
    session.state = State.AI_CHAT
    
    session, response = state_machine.process(session, "Привет, ИИ")
    
    # Проверяем, что сообщение добавлено в контекст
    assert len(session.ai_context) == 2  # user message + ai response
    assert session.ai_context[0]["role"] == "user"
    assert session.ai_context[0]["content"] == "Привет, ИИ"
    assert session.ai_context[1]["role"] == "assistant"


def test_terms_state(state_machine, session):
    """Тест состояния показа условий"""
    session.state = State.TERMS
    
    # Любое сообщение должно вернуть в меню
    session, response = state_machine.process(session, "ok")
    
    assert session.state == State.MENU
    assert "Главное меню" in response


def test_psy_question_state(state_machine, session):
    """Тест состояния вопроса по психологии"""
    session.state = State.PSY_QUESTION
    
    session, response = state_machine.process(session, "Как справиться со стрессом?")
    
    assert session.state == State.MENU
    assert "Спасибо за вопрос" in response
    assert "Главное меню" in response
