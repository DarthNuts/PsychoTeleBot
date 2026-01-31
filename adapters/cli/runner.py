import sys
from typing import Optional

from application.bot_service import BotService
from application.state_machine import StateMachine
from infrastructure.in_memory_repositories import (
    InMemorySessionRepository,
    InMemoryTicketRepository
)
from domain.models import TicketStatus


class CLIRunner:
    """CLI интерфейс для отладки бота без Telegram API"""

    def __init__(self):
        # Инициализация зависимостей
        session_repo = InMemorySessionRepository()
        ticket_repo = InMemoryTicketRepository()
        state_machine = StateMachine()
        
        self.bot_service = BotService(
            session_repo=session_repo,
            ticket_repo=ticket_repo,
            state_machine=state_machine
        )
        
        self.current_user_id = "test_user_1"
        self.running = True

    def print_banner(self):
        """Вывод приветственного баннера"""
        print("=" * 60)
        print("  PsychoTeleBot - CLI Debug Mode")
        print("=" * 60)
        print("\nДоступные команды:")
        print("  /start - начать диалог")
        print("  /menu - вернуться в меню")
        print("  /clear - очистить контекст ИИ")
        print("  /reset - сбросить сессию")
        print("  /user <id> - сменить пользователя")
        print("  /tickets - показать все заявки")
        print("  /quit - выход")
        print("=" * 60)
        print()

    def run(self):
        """Запуск CLI интерфейса"""
        self.print_banner()
        
        # Отправляем /start для инициализации
        self._process_message("/start")
        
        while self.running:
            try:
                # Показываем текущего пользователя
                user_input = input(f"\n[{self.current_user_id}] > ").strip()
                
                if not user_input:
                    continue
                
                # Обработка служебных команд CLI
                if user_input.startswith("/quit") or user_input.lower() == "exit":
                    self.running = False
                    print("\n👋 До свидания!")
                    break
                
                elif user_input.startswith("/reset"):
                    self._reset_session()
                    continue
                
                elif user_input.startswith("/user"):
                    self._change_user(user_input)
                    continue
                
                elif user_input.startswith("/tickets"):
                    self._show_tickets()
                    continue
                
                # Обработка сообщения через бота
                self._process_message(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 До свидания!")
                self.running = False
                break
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
                import traceback
                traceback.print_exc()

    def _process_message(self, message: str):
        """Обработка сообщения через бот"""
        response = self.bot_service.process_message(self.current_user_id, message)
        print(f"\n🤖 Бот:\n{response}")

    def _reset_session(self):
        """Сброс сессии текущего пользователя"""
        # Получаем репозитории из сервиса
        self.bot_service.session_repo.delete(self.current_user_id)
        print("\n✅ Сессия сброшена")
        self._process_message("/start")

    def _change_user(self, command: str):
        """Смена текущего пользователя"""
        parts = command.split()
        if len(parts) < 2:
            print("\n❌ Использование: /user <user_id>")
            return
        
        new_user_id = parts[1]
        self.current_user_id = new_user_id
        print(f"\n✅ Текущий пользователь: {self.current_user_id}")
        self._process_message("/start")

    def _show_tickets(self):
        """Показать все заявки"""
        tickets = self.bot_service.get_all_tickets()
        
        if not tickets:
            print("\n📋 Заявок нет")
            return
        
        print("\n" + "=" * 60)
        print("📋 Все заявки:")
        print("=" * 60)
        
        for ticket in tickets:
            print(f"\n🎫 ID: {ticket.id}")
            print(f"   Пользователь: {ticket.user_id}")
            print(f"   Тема: {ticket.topic}")
            print(f"   Статус: {ticket.status.value}")
            print(f"   Критичность: {ticket.severity.value}")
            print(f"   Возраст: {ticket.age}, Пол: {ticket.gender}")
            print(f"   Сообщение: {ticket.message[:50]}...")
            print(f"   Создано: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if ticket.assigned_to:
                print(f"   Назначено: {ticket.assigned_to}")
        
        print("=" * 60)


def main():
    """Точка входа для CLI"""
    runner = CLIRunner()
    runner.run()


if __name__ == "__main__":
    main()
