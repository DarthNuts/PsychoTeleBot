"""
Демонстрационный скрипт для проверки функциональности PsychoTeleBot
без запуска интерактивного CLI
"""

from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.in_memory_repositories import (
    InMemorySessionRepository,
    InMemoryTicketRepository
)


def demo_full_consultation():
    """Демонстрация полного процесса создания консультации"""
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ: Полный процесс консультации")
    print("=" * 60)
    
    # Инициализация
    session_repo = InMemorySessionRepository()
    ticket_repo = InMemoryTicketRepository()
    state_machine = StateMachine()
    bot_service = BotService(session_repo, ticket_repo, state_machine)
    
    user_id = "demo_user_1"
    
    # Сценарий
    messages = [
        ("/start", "Старт бота"),
        ("1", "Выбор консультации со специалистом"),
        ("Депрессия", "Тема консультации"),
        ("Мужской", "Пол"),
        ("30", "Возраст"),
        ("3", "Критичность - Высокая"),
        ("Чувствую себя очень плохо последние недели", "Описание проблемы"),
    ]
    
    for message, description in messages:
        print(f"\n>>> Пользователь ({description}): {message}")
        response = bot_service.process_message(user_id, message)
        print(f"<<< Бот:\n{response[:200]}...")
    
    # Проверяем созданную заявку
    tickets = bot_service.get_user_tickets(user_id)
    print("\n" + "=" * 60)
    print(f"Создано заявок: {len(tickets)}")
    if tickets:
        ticket = tickets[0]
        print(f"ID заявки: {ticket.id}")
        print(f"Тема: {ticket.topic}")
        print(f"Статус: {ticket.status.value}")
        print(f"Критичность: {ticket.severity.value}")
    print("=" * 60)


def demo_ai_chat():
    """Демонстрация работы с ИИ-чатом"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ: Чат с ИИ и очистка контекста")
    print("=" * 60)
    
    # Инициализация
    session_repo = InMemorySessionRepository()
    ticket_repo = InMemoryTicketRepository()
    state_machine = StateMachine()
    bot_service = BotService(session_repo, ticket_repo, state_machine)
    
    user_id = "demo_user_2"
    
    # Сценарий
    messages = [
        ("/start", "Старт"),
        ("2", "Выбор ИИ-консультации"),
        ("Привет, как справиться со стрессом?", "Вопрос к ИИ #1"),
        ("А что насчет медитации?", "Вопрос к ИИ #2"),
        ("/clear", "Очистка контекста"),
        ("Новый вопрос после очистки", "Новый вопрос"),
        ("/menu", "Возврат в меню"),
    ]
    
    for message, description in messages:
        print(f"\n>>> Пользователь ({description}): {message}")
        response = bot_service.process_message(user_id, message)
        print(f"<<< Бот:\n{response[:150]}...")
    
    print("=" * 60)


def demo_menu_from_any_state():
    """Демонстрация возврата в меню из любого состояния"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ: Возврат в меню из середины формы")
    print("=" * 60)
    
    # Инициализация
    session_repo = InMemorySessionRepository()
    ticket_repo = InMemoryTicketRepository()
    state_machine = StateMachine()
    bot_service = BotService(session_repo, ticket_repo, state_machine)
    
    user_id = "demo_user_3"
    
    # Сценарий
    messages = [
        ("/start", "Старт"),
        ("1", "Выбор консультации"),
        ("Тревога", "Начало заполнения"),
        ("Женский", "Пол"),
        ("/menu", "ВОЗВРАТ В МЕНЮ из середины формы"),
        ("3", "Выбор условий обращения"),
    ]
    
    for message, description in messages:
        print(f"\n>>> Пользователь ({description}): {message}")
        response = bot_service.process_message(user_id, message)
        print(f"<<< Бот:\n{response[:150]}...")
    
    print("=" * 60)


def main():
    """Запуск всех демонстраций"""
    print("\n" + "🤖 " * 20)
    print("PsychoTeleBot - Демонстрация функциональности")
    print("🤖 " * 20 + "\n")
    
    demo_full_consultation()
    demo_ai_chat()
    demo_menu_from_any_state()
    
    print("\n✅ Все демонстрации завершены успешно!")
    print("\nДля интерактивного тестирования запустите:")
    print("  python -m adapters.cli")
    print("\nДля запуска тестов:")
    print("  pytest -v\n")


if __name__ == "__main__":
    main()
