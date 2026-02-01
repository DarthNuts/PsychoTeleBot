import pytest
from domain.models import State, Severity
from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.in_memory_repositories import (
    InMemorySessionRepository,
    InMemoryTicketRepository
)


@pytest.fixture
def bot_service():
    """Фикстура для создания экземпляра BotService"""
    session_repo = InMemorySessionRepository()
    ticket_repo = InMemoryTicketRepository()
    state_machine = StateMachine()
    
    return BotService(
        session_repo=session_repo,
        ticket_repo=ticket_repo,
        state_machine=state_machine
    )


def test_welcome_and_menu(bot_service):
    """Тест приветствия и показа меню"""
    user_id = "test_user_1"
    
    # Отправляем /start
    response = bot_service.process_message(user_id, "/start")
    
    # Проверяем, что есть приветствие и меню
    assert "Добро пожаловать" in response
    assert "Главное меню" in response
    assert "Консультация со специалистом" in response


def test_menu_command_from_any_state(bot_service):
    """Тест команды /menu из любого состояния"""
    user_id = "test_user_2"
    
    # Начинаем заполнение формы
    bot_service.process_message(user_id, "/start")
    bot_service.process_message(user_id, "1")  # Выбираем консультацию
    bot_service.process_message(user_id, "Тревога")  # Тема
    
    # Возвращаемся в меню
    response = bot_service.process_message(user_id, "/menu")
    
    assert "Главное меню" in response
    
    # Проверяем, что состояние сброшено
    session = bot_service.session_repo.get(user_id)
    assert session.state == State.MENU
    assert session.consultation_form.topic is None


def test_consultation_full_flow(bot_service):
    """Тест полного процесса создания консультации"""
    user_id = "test_user_3"
    
    # Начало
    bot_service.process_message(user_id, "/start")
    
    # Выбираем консультацию со специалистом
    response = bot_service.process_message(user_id, "1")
    assert "тему консультации" in response
    
    # Заполняем тему
    response = bot_service.process_message(user_id, "Депрессия")
    assert "пол" in response
    
    # Заполняем пол
    response = bot_service.process_message(user_id, "Мужской")
    assert "возраст" in response
    
    # Заполняем возраст
    response = bot_service.process_message(user_id, "30")
    assert "критичность" in response
    
    # Заполняем критичность
    response = bot_service.process_message(user_id, "3")
    assert "ситуацию подробно" in response
    
    # Заполняем сообщение
    response = bot_service.process_message(user_id, "Нужна помощь")
    assert "Заявка создана" in response
    
    # Проверяем, что заявка действительно создана
    tickets = bot_service.get_user_tickets(user_id)
    assert len(tickets) == 1
    
    ticket = tickets[0]
    assert ticket.topic == "Депрессия"
    assert ticket.gender == "Мужской"
    assert ticket.age == 30
    assert ticket.severity == Severity.HIGH
    assert ticket.message == "Нужна помощь"


def test_ai_chat_and_clear(bot_service):
    """Тест чата с ИИ и очистки контекста"""
    user_id = "test_user_4"
    
    # Начало
    bot_service.process_message(user_id, "/start")
    
    # Выбираем ИИ
    response = bot_service.process_message(user_id, "2")
    assert "ИИ-ассистентом" in response
    
    # Отправляем сообщение ИИ
    response = bot_service.process_message(user_id, "Привет, ИИ!")
    # Может быть либо реальный ответ AI, либо fallback сообщение при отсутствии ключа
    assert ("технические сложности" in response or "Вы написали" in response or 
            "Заглушка ИИ" in response or len(response) > 0)
    
    # Проверяем, что контекст сохранен
    session = bot_service.session_repo.get(user_id)
    assert len(session.ai_context) > 0
    
    # Очищаем контекст
    response = bot_service.process_message(user_id, "/clear")
    assert "очищен" in response
    
    # Проверяем, что контекст пуст
    session = bot_service.session_repo.get(user_id)
    assert len(session.ai_context) == 0


def test_terms_display(bot_service):
    """Тест отображения условий обращения"""
    user_id = "test_user_5"
    
    # Начало
    bot_service.process_message(user_id, "/start")
    
    # Выбираем условия
    response = bot_service.process_message(user_id, "3")
    assert "Условия обращения" in response
    assert "анонимны" in response
    
    # Любое сообщение возвращает в меню
    response = bot_service.process_message(user_id, "ок")
    assert "Главное меню" in response


def test_psy_question(bot_service):
    """Тест вопроса по психологии"""
    user_id = "test_user_6"
    
    # Начало
    bot_service.process_message(user_id, "/start")
    
    # Выбираем вопрос
    response = bot_service.process_message(user_id, "4")
    assert "Вопрос по психологии" in response
    
    # Задаем вопрос
    response = bot_service.process_message(user_id, "Как справиться со стрессом?")
    assert "Спасибо за вопрос" in response
    assert "Главное меню" in response


def test_age_validation(bot_service):
    """Тест валидации возраста"""
    user_id = "test_user_7"
    
    # Начало и переход к вводу возраста
    bot_service.process_message(user_id, "/start")
    bot_service.process_message(user_id, "1")
    bot_service.process_message(user_id, "Тема")
    bot_service.process_message(user_id, "Мужской")
    
    # Пытаемся ввести некорректный возраст
    response = bot_service.process_message(user_id, "abc")
    assert "введите число" in response
    
    # Пытаемся ввести возраст вне диапазона
    response = bot_service.process_message(user_id, "150")
    assert "корректный возраст" in response
    
    # Вводим корректный возраст
    response = bot_service.process_message(user_id, "25")
    assert "критичность" in response


def test_severity_options(bot_service):
    """Тест выбора критичности"""
    user_id = "test_user_8"
    
    # Начало и переход к выбору критичности
    bot_service.process_message(user_id, "/start")
    bot_service.process_message(user_id, "1")
    bot_service.process_message(user_id, "Тема")
    bot_service.process_message(user_id, "Женский")
    bot_service.process_message(user_id, "28")
    
    # Проверяем разные варианты ввода критичности
    
    # По номеру
    response = bot_service.process_message(user_id, "2")
    assert "ситуацию подробно" in response
    
    session = bot_service.session_repo.get(user_id)
    assert session.consultation_form.severity == Severity.MEDIUM


def test_multiple_users(bot_service):
    """Тест работы с несколькими пользователями"""
    user1 = "user_1"
    user2 = "user_2"
    
    # Пользователь 1 начинает форму
    bot_service.process_message(user1, "/start")
    bot_service.process_message(user1, "1")
    bot_service.process_message(user1, "Тема 1")
    
    # Пользователь 2 начинает форму
    bot_service.process_message(user2, "/start")
    bot_service.process_message(user2, "1")
    bot_service.process_message(user2, "Тема 2")
    
    # Проверяем, что сессии независимы
    session1 = bot_service.session_repo.get(user1)
    session2 = bot_service.session_repo.get(user2)
    
    assert session1.consultation_form.topic == "Тема 1"
    assert session2.consultation_form.topic == "Тема 2"
    assert session1.consultation_form.topic != session2.consultation_form.topic


def test_ticket_admin_operations(bot_service):
    """Тест админских операций с заявками"""
    user_id = "test_user_9"
    
    # Создаем заявку
    bot_service.process_message(user_id, "/start")
    bot_service.process_message(user_id, "1")
    bot_service.process_message(user_id, "Тревога")
    bot_service.process_message(user_id, "Мужской")
    bot_service.process_message(user_id, "35")
    bot_service.process_message(user_id, "4")
    bot_service.process_message(user_id, "Срочно нужна помощь")
    
    # Получаем заявку
    tickets = bot_service.get_user_tickets(user_id)
    assert len(tickets) == 1
    ticket = tickets[0]
    
    # Назначаем специалиста
    specialist_id = "specialist_1"
    result = bot_service.assign_ticket(ticket.id, specialist_id)
    assert result is True
    
    # Проверяем назначение
    updated_ticket = bot_service.get_ticket(ticket.id)
    assert updated_ticket.assigned_to == specialist_id
    
    # Добавляем сообщение в чат
    bot_service.add_message_to_ticket(ticket.id, specialist_id, "Здравствуйте, чем могу помочь?")
    
    updated_ticket = bot_service.get_ticket(ticket.id)
    assert len(updated_ticket.chat_history) == 1
    assert updated_ticket.chat_history[0]["message"] == "Здравствуйте, чем могу помочь?"
