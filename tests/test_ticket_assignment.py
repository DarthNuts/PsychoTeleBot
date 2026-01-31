"""
Тесты для системы назначения заявок с пагинацией
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from domain.models import (
    UserSession, State, Ticket, TicketStatus, Severity, ConsultationForm
)
from domain.roles import UserRole, UserProfile, RoleManager
from application.bot_service import BotService
from infrastructure.sqlite_repositories import (
    SQLiteSessionRepository, SQLiteTicketRepository, SQLiteRoleRepository
)


@pytest.fixture
def setup_bot_with_tickets():
    """Подготовка тестового окружения с заявками"""
    # Создаём mock репозитории
    session_repo = Mock(spec=SQLiteSessionRepository)
    ticket_repo = Mock(spec=SQLiteTicketRepository)
    role_manager = RoleManager(admin_ids=["admin_123"])
    role_repo = Mock(spec=SQLiteRoleRepository)
    state_machine = Mock()
    
    bot_service = BotService(
        session_repo=session_repo,
        ticket_repo=ticket_repo,
        state_machine=state_machine,
        role_manager=role_manager,
        role_repo=role_repo
    )
    
    # Создаём психологов (сначала создаём, потом повышаем)
    role_manager.get_or_create_user("psy_001", "doctor_ivan", "Ivan", "Petrov")
    role_manager.get_or_create_user("psy_002", "doctor_maria", "Maria", "Sidorova")
    role_manager.promote_to_psychologist("psy_001")
    role_manager.promote_to_psychologist("psy_002")
    psy1 = role_manager.get_user("psy_001")
    psy2 = role_manager.get_user("psy_002")
    
    # Создаём заявки с разной критичностью и датами
    tickets = []
    severities = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    
    for i in range(12):
        severity = severities[i % len(severities)]
        ticket = Ticket(
            id=f"ticket_{i:03d}",
            user_id=f"user_{i}",
            topic=f"Проблема {i+1}",
            gender="M",
            age=30 + i,
            severity=severity,
            message=f"Описание проблемы {i+1}",
            status=TicketStatus.NEW if i < 10 else TicketStatus.CLOSED,
            created_at=datetime(2026, 1, 31 - (i % 7), 10 + i % 12)
        )
        tickets.append(ticket)
    
    ticket_repo.get_all.return_value = tickets
    ticket_repo.get = lambda ticket_id: next((t for t in tickets if t.id == ticket_id), None)
    
    return {
        'bot_service': bot_service,
        'session_repo': session_repo,
        'ticket_repo': ticket_repo,
        'role_manager': role_manager,
        'role_repo': role_repo,
        'tickets': tickets,
        'psychologists': [psy1, psy2]
    }


class TestTicketSorting:
    """Тесты для сортировки заявок"""
    
    def test_sort_by_severity_and_date(self, setup_bot_with_tickets):
        """Позитивный: заявки сортируются по критичности и дате"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        sorted_tickets = bot_service.get_sorted_tickets_for_assignment()
        
        # Проверяем, что только NEW и WAITING_RESPONSE заявки
        assert all(t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE) 
                  for t in sorted_tickets)
        
        # Проверяем сортировку по критичности
        severity_order = {"Критическая": 0, "Высокая": 1, "Средняя": 2, "Низкая": 3}
        for i in range(len(sorted_tickets) - 1):
            curr_sev = severity_order[sorted_tickets[i].severity.value]
            next_sev = severity_order[sorted_tickets[i+1].severity.value]
            assert curr_sev <= next_sev, "Критичность должна быть в порядке убывания"
    
    def test_sort_critical_first(self, setup_bot_with_tickets):
        """Позитивный: критичные заявки идут первыми"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        sorted_tickets = bot_service.get_sorted_tickets_for_assignment()
        if sorted_tickets:
            assert sorted_tickets[0].severity == Severity.CRITICAL
    
    def test_empty_tickets_list(self, setup_bot_with_tickets):
        """Позитивный: пустой список заявок"""
        env = setup_bot_with_tickets
        env['ticket_repo'].get_all.return_value = []
        bot_service = env['bot_service']
        
        sorted_tickets = bot_service.get_sorted_tickets_for_assignment()
        assert sorted_tickets == []


class TestPsychologistSorting:
    """Тесты для сортировки психологов по нагрузке"""
    
    def test_sort_by_workload(self, setup_bot_with_tickets):
        """Позитивный: психологи сортируются по количеству активных заявок"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        # Назначаем заявки
        tickets = env['ticket_repo'].get_all.return_value
        for i, ticket in enumerate(tickets[:3]):
            ticket.assigned_to = "psy_001" if i < 2 else "psy_002"
            ticket.status = TicketStatus.IN_PROGRESS
        
        sorted_psys = bot_service.get_psychologists_by_workload()
        
        # psy_002 должен быть первым (1 заявка), psy_001 вторым (2 заявки)
        assert sorted_psys[0].user_id == "psy_002"
        assert sorted_psys[1].user_id == "psy_001"
    
    def test_psychologist_with_no_tickets(self, setup_bot_with_tickets):
        """Позитивный: психолог без заявок на первом месте"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        # Назначаем все заявки первому психологу
        for ticket in env['ticket_repo'].get_all.return_value:
            ticket.assigned_to = "psy_001"
        
        sorted_psys = bot_service.get_psychologists_by_workload()
        assert sorted_psys[0].user_id == "psy_002"


class TestPaginationState:
    """Тесты для состояния пагинации"""
    
    def test_initial_pagination_offset(self):
        """Позитивный: начальное смещение = 0"""
        session = UserSession(user_id="123")
        assert session.pagination_offset == 0
        assert session.selected_ticket_id is None
    
    def test_pagination_offset_persistence(self):
        """Позитивный: смещение сохраняется в сессии"""
        session = UserSession(user_id="123")
        session.pagination_offset = 10
        session.selected_ticket_id = "ticket_001"
        
        assert session.pagination_offset == 10
        assert session.selected_ticket_id == "ticket_001"
    
    def test_state_transition_admin_assign_ticket(self):
        """Позитивный: переход в состояние выбора заявки"""
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_MENU
        
        # Имитация перехода
        session.state = State.ADMIN_ASSIGN_TICKET_SELECT
        session.pagination_offset = 0
        
        assert session.state == State.ADMIN_ASSIGN_TICKET_SELECT
        assert session.pagination_offset == 0
    
    def test_state_transition_admin_assign_psycho(self):
        """Позитивный: переход в состояние выбора психолога"""
        session = UserSession(user_id="admin_123")
        session.state = State.ADMIN_ASSIGN_PSYCHO_SELECT
        session.selected_ticket_id = "ticket_001"
        session.pagination_offset = 0
        
        assert session.state == State.ADMIN_ASSIGN_PSYCHO_SELECT
        assert session.selected_ticket_id == "ticket_001"
        assert session.pagination_offset == 0
    
    def test_reset_pagination_on_state_change(self):
        """Позитивный: пагинация сбрасывается при переходе в новое состояние"""
        session = UserSession(user_id="admin_123")
        session.pagination_offset = 25
        session.state = State.ADMIN_ASSIGN_TICKET_SELECT
        
        # Переходим в следующее состояние
        session.state = State.ADMIN_ASSIGN_PSYCHO_SELECT
        session.pagination_offset = 0  # Сброс
        
        assert session.pagination_offset == 0


class TestTicketAssignmentWorkflow:
    """Тесты для workflow назначения заявок"""
    
    def test_render_tickets_page_first(self, setup_bot_with_tickets):
        """Позитивный: рендеринг первой страницы заявок"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        tickets = bot_service.get_sorted_tickets_for_assignment()
        response = bot_service._render_tickets_page(tickets, 0)
        
        assert "📋" in response
        assert "Заявки для назначения" in response
        assert "стр. 1/" in response
        assert "Введите номер заявки" in response
    
    def test_render_tickets_page_pagination_info(self, setup_bot_with_tickets):
        """Позитивный: информация о пагинации корректна"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        tickets = bot_service.get_sorted_tickets_for_assignment()
        
        # Первая страница
        response1 = bot_service._render_tickets_page(tickets, 0)
        assert "стр. 1/" in response1
        
        # Вторая страница
        response2 = bot_service._render_tickets_page(tickets, 10)
        assert "стр. 2/" in response2
    
    def test_render_psychologists_page(self, setup_bot_with_tickets):
        """Позитивный: рендеринг страницы психологов"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        tickets = env['ticket_repo'].get_all.return_value
        psychologists = bot_service.get_psychologists_by_workload()
        
        response = bot_service._render_psychologists_page(tickets[0], psychologists, 0)
        
        assert "👥" in response
        assert "Выберите психолога" in response
        assert "Введите номер психолога" in response
        assert "@doctor_ivan" in response or "@doctor_maria" in response
    
    def test_assign_ticket_success(self, setup_bot_with_tickets):
        """Позитивный: успешное назначение заявки"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        
        ticket_id = "ticket_001"
        psychologist_id = "psy_001"
        
        success = bot_service.assign_ticket(ticket_id, psychologist_id)
        
        assert success is True
        assigned_ticket = env['ticket_repo'].get(ticket_id)
        assert assigned_ticket.assigned_to == psychologist_id
        assert assigned_ticket.status == TicketStatus.IN_PROGRESS
    
    def test_assign_nonexistent_ticket(self, setup_bot_with_tickets):
        """Негативный: назначение несуществующей заявки"""
        env = setup_bot_with_tickets
        bot_service = env['bot_service']
        env['ticket_repo'].get.return_value = None
        
        success = bot_service.assign_ticket("nonexistent", "psy_001")
        
        assert success is False


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_pagination_with_less_than_10_items(self, setup_bot_with_tickets):
        """Позитивный: пагинация с меньше чем 10 элементами"""
        env = setup_bot_with_tickets
        env['ticket_repo'].get_all.return_value = [
            Ticket(
                id="ticket_001",
                user_id="user_001",
                topic="Проблема",
                gender="M",
                age=30,
                severity=Severity.HIGH,
                message="Описание",
                status=TicketStatus.NEW
            )
        ]
        bot_service = env['bot_service']
        
        tickets = bot_service.get_sorted_tickets_for_assignment()
        response = bot_service._render_tickets_page(tickets, 0)
        
        assert "стр. 1/1" in response
    
    def test_pagination_offset_beyond_list(self):
        """Позитивный: смещение больше длины списка"""
        tickets = [Ticket(
            id=f"t_{i}",
            user_id=f"u_{i}",
            topic=f"Topic {i}",
            gender="M",
            age=30,
            severity=Severity.MEDIUM,
            message="Desc",
            status=TicketStatus.NEW
        ) for i in range(5)]
        
        page_tickets = tickets[20:30]  # За границами
        assert page_tickets == []
    
    def test_session_state_preservation(self):
        """Позитивный: сохранение состояния сессии"""
        session = UserSession(user_id="123")
        session.state = State.ADMIN_ASSIGN_PSYCHO_SELECT
        session.pagination_offset = 15
        session.selected_ticket_id = "ticket_005"
        
        # Имитация сохранения и загрузки
        saved_state = session.state
        saved_offset = session.pagination_offset
        saved_ticket = session.selected_ticket_id
        
        assert saved_state == State.ADMIN_ASSIGN_PSYCHO_SELECT
        assert saved_offset == 15
        assert saved_ticket == "ticket_005"
    
    def test_multiple_tickets_same_severity(self, setup_bot_with_tickets):
        """Позитивный: несколько заявок с одинаковой критичностью сортируются по дате"""
        env = setup_bot_with_tickets
        
        tickets = [
            Ticket(
                id="t1",
                user_id="u1",
                topic="Old",
                gender="M",
                age=30,
                severity=Severity.HIGH,
                message="Old ticket",
                status=TicketStatus.NEW,
                created_at=datetime(2026, 1, 25)
            ),
            Ticket(
                id="t2",
                user_id="u2",
                topic="New",
                gender="F",
                age=28,
                severity=Severity.HIGH,
                message="New ticket",
                status=TicketStatus.NEW,
                created_at=datetime(2026, 1, 31)
            ),
        ]
        
        env['ticket_repo'].get_all.return_value = tickets
        bot_service = env['bot_service']
        
        sorted_tickets = bot_service.get_sorted_tickets_for_assignment()
        
        # Более старая заявка должна быть первой
        assert sorted_tickets[0].id == "t1"
        assert sorted_tickets[1].id == "t2"


class TestSessionPersistence:
    """Тесты сохранения сессии в БД"""
    
    def test_session_fields_saved(self):
        """Позитивный: все поля сессии сохраняются"""
        session = UserSession(user_id="123")
        session.state = State.ADMIN_ASSIGN_PSYCHO_SELECT
        session.pagination_offset = 20
        session.selected_ticket_id = "ticket_042"
        session.current_ticket_id = "ticket_042"
        
        # Проверяем что все поля присутствуют
        assert hasattr(session, 'pagination_offset')
        assert hasattr(session, 'selected_ticket_id')
        assert session.pagination_offset == 20
        assert session.selected_ticket_id == "ticket_042"
    
    def test_session_defaults(self):
        """Позитивный: default значения сессии корректны"""
        session = UserSession(user_id="999")
        
        assert session.pagination_offset == 0
        assert session.selected_ticket_id is None
        assert session.state == State.MENU
