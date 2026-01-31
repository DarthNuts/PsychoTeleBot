"""
Тесты для команд админ-панели
"""
import pytest
from unittest.mock import Mock
from domain.models import UserSession, State, Ticket, TicketStatus, Severity
from domain.roles import UserRole, RoleManager
from application.bot_service import BotService


@pytest.fixture
def setup_admin_bot():
    """Подготовка тестового окружения с админом"""
    session_repo = Mock()
    ticket_repo = Mock()
    role_manager = RoleManager(admin_ids=["admin_123"])
    role_repo = Mock()
    state_machine = Mock()
    
    bot_service = BotService(
        session_repo=session_repo,
        ticket_repo=ticket_repo,
        state_machine=state_machine,
        role_manager=role_manager,
        role_repo=role_repo
    )
    
    # Создаём админа
    role_manager.get_or_create_user("admin_123", "admin_user", "Admin", "User")
    
    # Мок для ticket_repo
    ticket_repo.get_all.return_value = []
    
    return {
        'bot_service': bot_service,
        'session_repo': session_repo,
        'ticket_repo': ticket_repo,
        'role_manager': role_manager,
        'role_repo': role_repo
    }


class TestAdminMenuCommand:
    """Тесты команды /menu в админ-панели"""
    
    def test_menu_command_from_admin_menu(self, setup_admin_bot):
        """Позитивный: /menu из ADMIN_MENU возвращает в обычное меню"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MENU
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/menu", "admin_123"
        )
        
        assert updated_session.state == State.MENU
        assert "обычное меню" in response.lower()
    
    def test_menu_command_from_admin_manage_psychologists(self, setup_admin_bot):
        """Позитивный: /menu из ADMIN_MANAGE_PSYCHOLOGISTS возвращает в меню"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MANAGE_PSYCHOLOGISTS
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/menu", "admin_123"
        )
        
        assert updated_session.state == State.MENU
        assert "обычное меню" in response.lower()
    
    def test_menu_command_from_admin_assign_ticket(self, setup_admin_bot):
        """Позитивный: /menu из ADMIN_ASSIGN_TICKET_SELECT возвращает в меню"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_ASSIGN_TICKET_SELECT
        session.pagination_offset = 10
        session.selected_ticket_id = "ticket_001"
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/menu", "admin_123"
        )
        
        assert updated_session.state == State.MENU
        assert updated_session.pagination_offset == 0
        assert updated_session.selected_ticket_id is None
    
    def test_menu_command_from_admin_assign_psycho(self, setup_admin_bot):
        """Позитивный: /menu из ADMIN_ASSIGN_PSYCHO_SELECT сбрасывает состояние"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_ASSIGN_PSYCHO_SELECT
        session.pagination_offset = 5
        session.selected_ticket_id = "ticket_042"
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/menu", "admin_123"
        )
        
        assert updated_session.state == State.MENU
        assert updated_session.pagination_offset == 0
        assert updated_session.selected_ticket_id is None
    
    def test_menu_command_from_demote_psycho(self, setup_admin_bot):
        """Позитивный: /menu из ADMIN_DEMOTE_PSYCHO_SELECT возвращает в меню"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_DEMOTE_PSYCHO_SELECT
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/menu", "admin_123"
        )
        
        assert updated_session.state == State.MENU


class TestPsychologistMenuCommand:
    """Тесты команды /menu в панели психолога"""
    
    def test_menu_command_from_psy_menu(self, setup_admin_bot):
        """Позитивный: /menu из PSY_MENU возвращает в обычное меню"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        role_manager = env['role_manager']
        
        # Создаём психолога
        role_manager.get_or_create_user("psy_001", "doctor_ivan")
        role_manager.promote_to_psychologist("psy_001")
        
        session = UserSession(user_id="psy_001")
        session.state = State.PSY_MENU
        
        updated_session, response = bot_service._handle_psychologist_message(
            session, "/menu", "psy_001"
        )
        
        assert updated_session.state == State.MENU
        assert "обычное меню" in response.lower()
    
    def test_menu_command_from_psy_tickets_list(self, setup_admin_bot):
        """Позитивный: /menu из PSY_TICKETS_LIST возвращает в меню"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        role_manager = env['role_manager']
        
        role_manager.get_or_create_user("psy_001", "doctor_ivan")
        role_manager.promote_to_psychologist("psy_001")
        
        session = UserSession(user_id="psy_001")
        session.state = State.PSY_TICKETS_LIST
        
        updated_session, response = bot_service._handle_psychologist_message(
            session, "/menu", "psy_001"
        )
        
        assert updated_session.state == State.MENU


class TestStartCommand:
    """Тесты команды /start для админа и психолога"""
    
    def test_start_command_admin(self, setup_admin_bot):
        """Позитивный: /start для админа открывает админ-панель"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.MENU
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/start", "admin_123"
        )
        
        assert updated_session.state == State.ADMIN_MENU
        assert "АДМИН-ПАНЕЛЬ" in response
    
    def test_start_command_psychologist(self, setup_admin_bot):
        """Позитивный: /start для психолога открывает панель психолога"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        role_manager = env['role_manager']
        
        role_manager.get_or_create_user("psy_001", "doctor_ivan")
        role_manager.promote_to_psychologist("psy_001")
        
        session = UserSession(user_id="psy_001")
        session.state = State.MENU
        
        updated_session, response = bot_service._handle_psychologist_message(
            session, "/start", "psy_001"
        )
        
        assert updated_session.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in response


class TestMenuOption4:
    """Тесты опции '4' (Обычное меню) в админ-панели"""
    
    def test_option_4_from_admin_menu(self, setup_admin_bot):
        """Позитивный: выбор '4' из ADMIN_MENU"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MENU
        
        updated_session, response = bot_service._handle_admin_message(
            session, "4", "admin_123"
        )
        
        assert updated_session.state == State.MENU
        assert "обычное меню" in response.lower()
    
    def test_text_option_from_admin_menu(self, setup_admin_bot):
        """Позитивный: выбор 'обычное меню' текстом"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MENU
        
        updated_session, response = bot_service._handle_admin_message(
            session, "обычное меню", "admin_123"
        )
        
        assert updated_session.state == State.MENU


class TestEdgeCases:
    """Граничные случаи для команд"""
    
    def test_menu_command_case_insensitive(self, setup_admin_bot):
        """Позитивный: /menu работает в любом регистре"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MENU
        
        for command in ["/menu", "/MENU", "/Menu", "/MeNu"]:
            updated_session, response = bot_service._handle_admin_message(
                session, command, "admin_123"
            )
            assert updated_session.state == State.MENU
    
    def test_menu_command_with_spaces(self, setup_admin_bot):
        """Позитивный: /menu с пробелами"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MENU
        
        updated_session, response = bot_service._handle_admin_message(
            session, "  /menu  ", "admin_123"
        )
        
        assert updated_session.state == State.MENU
    
    def test_pagination_reset_on_menu(self, setup_admin_bot):
        """Позитивный: пагинация сбрасывается при /menu"""
        env = setup_admin_bot
        bot_service = env['bot_service']
        
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_ASSIGN_TICKET_SELECT
        session.pagination_offset = 25
        session.selected_ticket_id = "test_ticket"
        
        updated_session, response = bot_service._handle_admin_message(
            session, "/menu", "admin_123"
        )
        
        assert updated_session.pagination_offset == 0
        assert updated_session.selected_ticket_id is None
