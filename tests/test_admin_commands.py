"""
Тесты для команд админ-панели
"""
import pytest
from datetime import datetime
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
        'role_repo': role_repo,
        'state_machine': state_machine
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
        """Позитивный: /menu из PSY_MENU показывает панель психолога"""
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
        
        assert updated_session.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in response
    
    def test_menu_command_from_psy_tickets_list(self, setup_admin_bot):
        """Позитивный: /menu из PSY_TICKETS_LIST возвращает в панель психолога"""
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
        
        assert updated_session.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in response


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


def _make_ticket(id_str, topic="Тест", status=TicketStatus.NEW, user_id="user_1", assigned_to=None):
    """Хелпер для создания тикета"""
    return Ticket(
        id=id_str, user_id=user_id, topic=topic, gender="М", age=25,
        severity=Severity.MEDIUM, message="msg", status=status,
        created_at=datetime(2026, 1, 1), assigned_to=assigned_to
    )


class TestPsychologistQueuePagination:
    """Тесты пагинации в очереди заявок психолога"""

    def _setup_psy(self, env):
        role_manager = env['role_manager']
        role_manager.get_or_create_user("psy_001", "doctor")
        role_manager.promote_to_psychologist("psy_001")

    def test_queue_shows_first_page(self, setup_admin_bot):
        """Позитивный: очередь заявок показывает первую страницу с пагинацией"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}") for i in range(15)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_MENU)
        s, r = env['bot_service']._handle_psychologist_message(session, "1", "psy_001")

        assert s.state == State.PSY_TICKETS_LIST
        assert s.pagination_offset == 0
        assert "стр. 1/2" in r
        assert "Всего: 15" in r

    def test_queue_empty(self, setup_admin_bot):
        """Позитивный: пустая очередь возвращает в PSY_MENU"""
        env = setup_admin_bot
        self._setup_psy(env)
        env['ticket_repo'].get_all.return_value = []

        session = UserSession(user_id="psy_001", state=State.PSY_MENU)
        s, r = env['bot_service']._handle_psychologist_message(session, "1", "psy_001")

        assert s.state == State.PSY_MENU
        assert "Нет заявок" in r

    def test_queue_next_page(self, setup_admin_bot):
        """Позитивный: далее переключает на следующую страницу"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}") for i in range(15)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        session.pagination_offset = 0
        s, r = env['bot_service']._handle_psychologist_message(session, "далее", "psy_001")

        assert s.pagination_offset == 10
        assert "стр. 2/2" in r

    def test_queue_next_page_last(self, setup_admin_bot):
        """Граничный: далее на последней странице не меняет offset"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}") for i in range(15)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        session.pagination_offset = 10
        s, r = env['bot_service']._handle_psychologist_message(session, "далее", "psy_001")

        assert s.pagination_offset == 10
        assert "последняя страница" in r

    def test_queue_prev_page(self, setup_admin_bot):
        """Позитивный: назад переключает на предыдущую страницу"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}") for i in range(15)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        session.pagination_offset = 10
        s, r = env['bot_service']._handle_psychologist_message(session, "назад", "psy_001")

        assert s.pagination_offset == 0
        assert "стр. 1/2" in r

    def test_queue_cancel_returns_to_psy_menu(self, setup_admin_bot):
        """Позитивный: отмена возвращает в меню психолога"""
        env = setup_admin_bot
        self._setup_psy(env)
        env['ticket_repo'].get_all.return_value = []

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        s, r = env['bot_service']._handle_psychologist_message(session, "отмена", "psy_001")

        assert s.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in r

    def test_queue_select_ticket(self, setup_admin_bot):
        """Позитивный: выбор заявки по номеру открывает её"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"ticket-{i}", f"Тема {i}") for i in range(3)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        session.pagination_offset = 0
        s, r = env['bot_service']._handle_psychologist_message(session, "2", "psy_001")

        assert s.state == State.PSY_TICKET_OPEN
        assert s.selected_ticket_id == "ticket-1"
        assert "Тема 1" in r

    def test_queue_select_invalid_number(self, setup_admin_bot):
        """Негативный: номер больше количества заявок"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}") for i in range(3)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        session.pagination_offset = 0
        s, r = env['bot_service']._handle_psychologist_message(session, "5", "psy_001")

        assert "не найдена" in r

    def test_queue_select_invalid_text(self, setup_admin_bot):
        """Негативный: неизвестный текст в списке заявок"""
        env = setup_admin_bot
        self._setup_psy(env)
        env['ticket_repo'].get_all.return_value = []

        session = UserSession(user_id="psy_001", state=State.PSY_TICKETS_LIST)
        s, r = env['bot_service']._handle_psychologist_message(session, "абвгд", "psy_001")

        assert "Введите номер" in r


class TestPsychologistMyTicketsPagination:
    """Тесты пагинации в 'Мои заявки' психолога"""

    def _setup_psy(self, env):
        role_manager = env['role_manager']
        role_manager.get_or_create_user("psy_001", "doctor")
        role_manager.promote_to_psychologist("psy_001")

    def test_my_tickets_shows_first_page(self, setup_admin_bot):
        """Позитивный: мои заявки показывают первую страницу"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
                   for i in range(12)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_MENU)
        s, r = env['bot_service']._handle_psychologist_message(session, "2", "psy_001")

        assert s.state == State.PSY_MY_TICKETS
        assert s.pagination_offset == 0
        assert "стр. 1/2" in r
        assert "Всего: 12" in r

    def test_my_tickets_empty(self, setup_admin_bot):
        """Позитивный: нет заявок в работе"""
        env = setup_admin_bot
        self._setup_psy(env)
        env['ticket_repo'].get_all.return_value = []

        session = UserSession(user_id="psy_001", state=State.PSY_MENU)
        s, r = env['bot_service']._handle_psychologist_message(session, "2", "psy_001")

        assert "нет заявок" in r.lower()

    def test_my_tickets_next_page(self, setup_admin_bot):
        """Позитивный: далее в моих заявках"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"t{i}", f"Тема {i}", assigned_to="psy_001") for i in range(15)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_MY_TICKETS)
        session.pagination_offset = 0
        s, r = env['bot_service']._handle_psychologist_message(session, "далее", "psy_001")

        assert s.pagination_offset == 10
        assert "стр. 2/2" in r

    def test_my_tickets_cancel_returns_to_psy_menu(self, setup_admin_bot):
        """Позитивный: отмена возвращает в меню психолога"""
        env = setup_admin_bot
        self._setup_psy(env)
        env['ticket_repo'].get_all.return_value = []

        session = UserSession(user_id="psy_001", state=State.PSY_MY_TICKETS)
        s, r = env['bot_service']._handle_psychologist_message(session, "отмена", "psy_001")

        assert s.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in r

    def test_my_tickets_select_ticket(self, setup_admin_bot):
        """Позитивный: выбор заявки по номеру"""
        env = setup_admin_bot
        self._setup_psy(env)
        tickets = [_make_ticket(f"my-t{i}", f"Моя тема {i}", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
                   for i in range(3)]
        env['ticket_repo'].get_all.return_value = tickets

        session = UserSession(user_id="psy_001", state=State.PSY_MY_TICKETS)
        session.pagination_offset = 0
        s, r = env['bot_service']._handle_psychologist_message(session, "1", "psy_001")

        assert s.state == State.PSY_TICKET_OPEN
        assert s.selected_ticket_id == "my-t0"
        assert "Моя тема 0" in r
        assert "Изменить статус" in r


class TestPsychologistTicketOpen:
    """Тесты карточки заявки (PSY_TICKET_OPEN)"""

    def _setup_psy(self, env):
        role_manager = env['role_manager']
        role_manager.get_or_create_user("psy_001", "doctor")
        role_manager.promote_to_psychologist("psy_001")

    def test_take_ticket(self, setup_admin_bot):
        """Позитивный: взять заявку в работу из очереди"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема 100", TicketStatus.NEW)
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "1", "psy_001")

        assert s.state == State.PSY_MENU
        assert "взята в работу" in r.lower()

    def test_back_to_queue(self, setup_admin_bot):
        """Позитивный: назад к списку из очереди"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема 100", TicketStatus.NEW)
        queue = [_make_ticket(f"t{i}", f"Тема {i}") for i in range(3)]
        env['ticket_repo'].get.return_value = ticket
        env['ticket_repo'].get_all.return_value = queue

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "0", "psy_001")

        assert s.state == State.PSY_TICKETS_LIST
        assert "Очередь заявок" in r

    def test_back_to_my_tickets(self, setup_admin_bot):
        """Позитивный: назад к 'моим заявкам'"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема 100", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        my_tickets = [ticket]
        env['ticket_repo'].get.return_value = ticket
        env['ticket_repo'].get_all.return_value = my_tickets

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "0", "psy_001")

        assert s.state == State.PSY_MY_TICKETS
        assert "Мои заявки" in r

    def test_change_status_option(self, setup_admin_bot):
        """Позитивный: открыть смену статуса из своей заявки"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема 100", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "1", "psy_001")

        assert s.state == State.PSY_CHANGE_STATUS
        assert "Выберите новый статус" in r

    def test_invalid_input(self, setup_admin_bot):
        """Негативный: неизвестная команда в карточке заявки"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема 100", TicketStatus.NEW)
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "привет", "psy_001")

        assert "Введите 1" in r


class TestPsychologistChangeStatus:
    """Тесты смены статуса заявки (PSY_CHANGE_STATUS)"""

    def _setup_psy(self, env):
        role_manager = env['role_manager']
        role_manager.get_or_create_user("psy_001", "doctor")
        role_manager.promote_to_psychologist("psy_001")

    def test_change_to_in_progress(self, setup_admin_bot):
        """Позитивный: смена статуса на 'В работе'"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема", TicketStatus.NEW, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_CHANGE_STATUS)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "1", "psy_001")

        assert s.state == State.PSY_MENU
        assert "В работе" in r
        env['ticket_repo'].update.assert_called_once()

    def test_change_to_closed(self, setup_admin_bot):
        """Позитивный: закрыть заявку"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_CHANGE_STATUS)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "3", "psy_001")

        assert s.state == State.PSY_MENU
        assert "Закрыто" in r

    def test_cancel_returns_to_ticket(self, setup_admin_bot):
        """Позитивный: отмена возвращает к карточке заявки"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема 100", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_CHANGE_STATUS)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "0", "psy_001")

        assert s.state == State.PSY_TICKET_OPEN
        assert "Тема 100" in r

    def test_invalid_input(self, setup_admin_bot):
        """Негативный: неверный ввод при смене статуса"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-100", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_CHANGE_STATUS)
        session.selected_ticket_id = "t-100"
        s, r = env['bot_service']._handle_psychologist_message(session, "абвгд", "psy_001")

        assert "Введите номер статуса" in r


class TestPsychologistChat:
    """Тесты чата психолога с пользователем"""

    def _setup_psy(self, env):
        role_manager = env['role_manager']
        role_manager.get_or_create_user("psy_001", "doctor")
        role_manager.promote_to_psychologist("psy_001")

    def _setup_session_repo(self, env, sessions: dict):
        """Настроить session_repo.get для возврата нужных сессий"""
        def get_session(uid):
            return sessions.get(uid)
        env['session_repo'].get.side_effect = get_session

    def test_start_chat(self, setup_admin_bot):
        """Позитивный: психолог начинает чат с пользователем"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.MENU)
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "2", "psy_001")

        assert s.state == State.PSY_TICKET_CHAT
        assert s.active_chat_ticket_id == "t-1"
        assert "Чат начат" in r
        # Проверяем сессию клиента
        assert client_session.state == State.USER_IN_CHAT
        assert client_session.active_chat_ticket_id == "t-1"
        # Проверяем уведомление
        notifications = env['bot_service'].get_pending_notifications()
        assert len(notifications) == 1
        assert notifications[0][0] == "user_1"
        assert "Чат начат" in notifications[0][1]

    def test_start_chat_already_active(self, setup_admin_bot):
        """Позитивный: если чат уже активен, '2' закрывает его"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "2", "psy_001")

        # Чат закрыт, клиент вернулся в меню
        assert client_session.state == State.MENU
        assert client_session.active_chat_ticket_id is None

    def test_close_chat_from_ticket_card(self, setup_admin_bot):
        """Позитивный: закрыть чат из карточки заявки"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_OPEN)
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "2", "psy_001")

        # Клиент возвращён в меню
        assert client_session.state == State.MENU
        assert client_session.active_chat_ticket_id is None
        # Уведомление клиенту
        notifications = env['bot_service'].get_pending_notifications()
        assert len(notifications) == 1
        assert "завершён" in notifications[0][1]

    def test_psy_sends_message_in_chat(self, setup_admin_bot):
        """Позитивный: психолог отправляет сообщение пользователю"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        session.active_chat_ticket_id = "t-1"
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "Привет, как дела?", "psy_001")

        assert "отправлено" in r.lower()
        # Проверяем уведомление пользователю
        notifications = env['bot_service'].get_pending_notifications()
        assert len(notifications) == 1
        assert notifications[0][0] == "user_1"
        assert "Привет, как дела?" in notifications[0][1]

    def test_psy_ends_chat_with_end_command(self, setup_admin_bot):
        """Позитивный: психолог завершает чат командой /end"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        session.active_chat_ticket_id = "t-1"
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "/end", "psy_001")

        assert s.state == State.PSY_TICKET_OPEN
        assert s.active_chat_ticket_id is None
        assert "завершён" in r.lower()
        # Клиент вернулся в меню
        assert client_session.state == State.MENU

    def test_user_sends_message_in_chat(self, setup_admin_bot):
        """Позитивный: пользователь отправляет сообщение психологу"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        session.active_chat_ticket_id = "t-1"
        s, r = env['bot_service']._handle_user_in_chat(session, "Мне грустно")

        assert "отправлено" in r.lower()
        notifications = env['bot_service'].get_pending_notifications()
        assert len(notifications) == 1
        assert notifications[0][0] == "psy_001"
        assert "Мне грустно" in notifications[0][1]

    def test_user_ends_chat_with_end(self, setup_admin_bot):
        """Позитивный: пользователь завершает чат командой /end"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        psy_session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        psy_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"psy_001": psy_session})

        session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        session.active_chat_ticket_id = "t-1"
        s, r = env['bot_service']._handle_user_in_chat(session, "/end")

        assert s.state == State.MENU
        assert s.active_chat_ticket_id is None
        assert "завершён" in r.lower()
        # Психолог вернулся в карточку заявки
        assert psy_session.state == State.PSY_TICKET_OPEN
        # Уведомление психологу
        notifications = env['bot_service'].get_pending_notifications()
        assert len(notifications) == 1
        assert notifications[0][0] == "psy_001"

    def test_get_pending_notifications_clears_queue(self, setup_admin_bot):
        """Позитивный: получение уведомлений очищает очередь"""
        env = setup_admin_bot
        bs = env['bot_service']
        bs.pending_notifications.append(("user_1", "test"))
        bs.pending_notifications.append(("user_2", "test2"))

        notifications = bs.get_pending_notifications()
        assert len(notifications) == 2
        assert len(bs.pending_notifications) == 0

    def test_psy_menu_after_end_works(self, setup_admin_bot):
        """Регресс: /menu работает после /end (чат → карточка → меню)"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        # Шаг 1: /end из чата
        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        session.active_chat_ticket_id = "t-1"
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "/end", "psy_001")
        assert s.state == State.PSY_TICKET_OPEN

        # Шаг 2: /menu должна вернуть панель психолога
        s2, r2 = env['bot_service']._handle_psychologist_message(s, "/menu", "psy_001")
        assert s2.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in r2

    def test_psy_start_after_end_works(self, setup_admin_bot):
        """Регресс: /start работает после /end"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        session.active_chat_ticket_id = "t-1"
        session.selected_ticket_id = "t-1"
        s, _ = env['bot_service']._handle_psychologist_message(session, "/end", "psy_001")
        assert s.state == State.PSY_TICKET_OPEN

        s2, r2 = env['bot_service']._handle_psychologist_message(s, "/start", "psy_001")
        assert s2.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in r2

    def test_psy_menu_from_chat_closes_chat(self, setup_admin_bot):
        """Позитивный: /menu из режима чата завершает чат и возвращает в меню"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        session.active_chat_ticket_id = "t-1"
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "/menu", "psy_001")

        assert s.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in r
        assert client_session.state == State.MENU
        assert s.active_chat_ticket_id is None

    def test_psy_start_from_chat_closes_chat(self, setup_admin_bot):
        """Позитивный: /start из режима чата завершает чат и возвращает в меню"""
        env = setup_admin_bot
        self._setup_psy(env)
        ticket = _make_ticket("t-1", "Тема", TicketStatus.IN_PROGRESS, assigned_to="psy_001")
        env['ticket_repo'].get.return_value = ticket

        client_session = UserSession(user_id="user_1", state=State.USER_IN_CHAT)
        client_session.active_chat_ticket_id = "t-1"
        self._setup_session_repo(env, {"user_1": client_session})

        session = UserSession(user_id="psy_001", state=State.PSY_TICKET_CHAT)
        session.active_chat_ticket_id = "t-1"
        session.selected_ticket_id = "t-1"
        s, r = env['bot_service']._handle_psychologist_message(session, "/start", "psy_001")

        assert s.state == State.PSY_MENU
        assert "ПАНЕЛЬ ПСИХОЛОГА" in r
        assert client_session.state == State.MENU
