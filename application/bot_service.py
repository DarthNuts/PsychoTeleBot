from typing import Optional
from datetime import datetime
import uuid

from domain.models import UserSession, Ticket, State, TicketStatus
from domain.repositories import SessionRepository, TicketRepository, RoleRepository
from domain.roles import UserRole, RoleManager, UserProfile
from application.state_machine import StateMachine


class BotService:
    """Основной сервис бота, координирующий все операции"""

    def __init__(
        self,
        session_repo: SessionRepository,
        ticket_repo: TicketRepository,
        state_machine: StateMachine,
        role_manager: RoleManager = None,
        role_repo: RoleRepository = None
    ):
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.state_machine = state_machine
        self.role_manager = role_manager or RoleManager()
        self.role_repo = role_repo

    def process_message(self, user_id: str, message: str, 
                       username: str = None, first_name: str = None, 
                       last_name: str = None) -> str:
        """
        Обработка сообщения от пользователя
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            username: Username пользователя (Telegram)
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            str: Ответ бота
        """
        # Получаем или создаем профиль пользователя
        user_profile = self.role_manager.get_or_create_user(
            user_id, username, first_name, last_name
        )
        
        # Сохраняем профиль в БД
        if self.role_repo:
            self.role_repo.save_user(user_profile)
        
        # Получаем или создаем сессию
        session = self.session_repo.get(user_id)
        if session is None:
            session = UserSession(user_id=user_id, state=State.MENU)
            self.session_repo.save(session)

        # Запоминаем предыдущее состояние
        previous_state = session.state
        
        # Проверяем роль и выбираем обработчик
        if self.role_manager.is_admin(user_id):
            # Админ меню
            session, response = self._handle_admin_message(session, message, user_id)
        elif self.role_manager.is_psychologist(user_id):
            # Психолог меню
            session, response = self._handle_psychologist_message(session, message, user_id)
        else:
            # Обычный пользователь
            session, response = self.state_machine.process(session, message)
        
        # Если завершили форму консультации, создаем заявку
        if (previous_state == State.CONSULT_FORM_MESSAGE and 
            session.state == State.MENU and 
            session.consultation_form.is_complete()):
            
            ticket = self._create_ticket_from_form(session)
            session.current_ticket_id = ticket.id
            session.reset_form()
        
        # Сохраняем сессию
        self.session_repo.save(session)
        
        return response

    def _handle_admin_message(self, session: UserSession, message: str, user_id: str) -> tuple:
        """Обработка сообщений администратора"""
        message_lower = message.strip().lower()
        
        if session.state == State.MENU or message_lower in ['/start', 'start']:
            session.state = State.ADMIN_MENU
            response = """👑 *АДМИН-ПАНЕЛЬ*

Выберите действие:
1️⃣ Управление психологами
2️⃣ Все заявки
3️⃣ Назначить на заявку
4️⃣ Обычное меню

Команды:
/menu - вернуться в обычное меню"""
            return session, response
        
        elif session.state == State.ADMIN_MENU:
            if message_lower in ['1', 'управление психологами']:
                session.state = State.ADMIN_MANAGE_PSYCHOLOGISTS
                psychologists = self.role_manager.list_psychologists()
                
                if not psychologists:
                    response = "Психологи не назначены\n\nДля добавления отправьте ID или @username пользователя:"
                else:
                    response = "👥 Текущие психологи:\n"
                    for psy in psychologists:
                        name = f"{psy.first_name or ''} {psy.last_name or ''}".strip()
                        username = f"@{psy.username}" if psy.username else ""
                        response += f"\n• {psy.user_id} ({username or name or 'нет имени'})"
                    response += "\n\nДля добавления нового отправьте ID или @username:"
                
                return session, response
            
            elif message_lower in ['2', 'все заявки']:
                tickets = self.ticket_repo.get_all()
                if not tickets:
                    response = "📋 Заявок нет"
                else:
                    response = "📋 Все заявки:\n"
                    for t in tickets[-10:]:  # Последние 10
                        response += f"\n• {t.id[:8]} - {t.topic} ({t.status.value})"
                return session, response
            
            elif message_lower in ['3', 'назначить на заявку']:
                tickets = self.get_sorted_tickets_for_assignment()
                
                if not tickets:
                    response = "📋 Нет заявок для назначения"
                    return session, response
                
                if not self.role_manager.list_psychologists():
                    response = "❌ Нет назначенных психологов\n\nСначала добавьте психологов через пункт 1"
                    return session, response
                
                # Показываем первую страницу заявок
                session.state = State.ADMIN_ASSIGN_TICKET_SELECT
                session.pagination_offset = 0
                response = self._render_tickets_page(tickets, session.pagination_offset)
                return session, response
            
            elif message_lower in ['4', 'обычное меню']:
                session.state = State.MENU
                return session, "Перешли в обычное меню"
        
        elif session.state == State.ADMIN_MANAGE_PSYCHOLOGISTS:
            # Принимаем ID (цифры) или username (с @ или без)
            identifier = message.strip()
            
            # Ищем пользователя по ID или username
            user_profile = self.role_manager.find_user(identifier)
            
            if not user_profile:
                response = f"❌ Пользователь '{identifier}' не найден\n\nПользователь должен сначала написать боту /start"
                session.state = State.ADMIN_MENU
                return session, response
            
            user_id_to_promote = user_profile.user_id
            display_name = f"@{user_profile.username}" if user_profile.username else user_id_to_promote
            
            # Проверяем текущую роль
            if self.role_manager.is_admin(user_id_to_promote):
                response = f"❌ Пользователь {display_name} является администратором\n\nАдминистратора нельзя назначить психологом"
            elif self.role_manager.is_psychologist(user_id_to_promote):
                response = f"✅ Пользователь {display_name} уже является психологом"
            else:
                # Назначаем роль
                success = self.role_manager.promote_to_psychologist(user_id_to_promote)
                if success:
                    # Сохраняем изменения в БД
                    if self.role_repo:
                        updated_profile = self.role_manager.get_user(user_id_to_promote)
                        self.role_repo.save_user(updated_profile)
                    response = f"✅ Пользователь {display_name} назначен психологом"
                else:
                    response = f"❌ Не удалось назначить роль психолога"
            
            session.state = State.ADMIN_MENU
            return session, response
        
        elif session.state == State.ADMIN_ASSIGN_TICKET_SELECT:
            # Обработка выбора заявки
            message_lower = message.strip().lower()
            
            tickets = self.get_sorted_tickets_for_assignment()
            
            if message_lower in ['exit', 'отмена', 'отмена', '0']:
                session.state = State.ADMIN_MENU
                response = "Отменено"
                return session, response
            
            elif message_lower in ['next', 'далее', 'следующие']:
                session.pagination_offset += 10
                if session.pagination_offset >= len(tickets):
                    session.pagination_offset -= 10
                    response = "✅ Это последняя страница"
                else:
                    response = self._render_tickets_page(tickets, session.pagination_offset)
                return session, response
            
            elif message_lower in ['prev', 'назад', 'предыдущие']:
                session.pagination_offset = max(0, session.pagination_offset - 10)
                response = self._render_tickets_page(tickets, session.pagination_offset)
                return session, response
            
            else:
                # Пытаемся выбрать заявку по номеру (1-10)
                try:
                    ticket_num = int(message.strip())
                    if 1 <= ticket_num <= 10:
                        idx = session.pagination_offset + ticket_num - 1
                        if idx < len(tickets):
                            session.selected_ticket_id = tickets[idx].id
                            session.state = State.ADMIN_ASSIGN_PSYCHO_SELECT
                            session.pagination_offset = 0  # Сбрасываем offset для психологов
                            
                            psychologists = self.get_psychologists_by_workload()
                            response = self._render_psychologists_page(tickets[idx], psychologists, 0)
                            return session, response
                        else:
                            response = "❌ Заявка не найдена"
                            return session, response
                except ValueError:
                    pass
                
                response = "❌ Неверный ввод. Введите номер заявки (1-10) или команду (далее/назад/отмена)"
                return session, response
        
        elif session.state == State.ADMIN_ASSIGN_PSYCHO_SELECT:
            # Обработка выбора психолога
            message_lower = message.strip().lower()
            
            if not session.selected_ticket_id:
                session.state = State.ADMIN_MENU
                return session, "❌ Ошибка: заявка не выбрана"
            
            psychologists = self.get_psychologists_by_workload()
            
            if message_lower in ['exit', 'отмена', '0']:
                session.state = State.ADMIN_ASSIGN_TICKET_SELECT
                session.selected_ticket_id = None
                response = self._render_tickets_page(self.get_sorted_tickets_for_assignment(), session.pagination_offset)
                return session, response
            
            elif message_lower in ['next', 'далее', 'следующие']:
                session.pagination_offset += 10
                if session.pagination_offset >= len(psychologists):
                    session.pagination_offset -= 10
                    response = "✅ Это последняя страница"
                else:
                    ticket = self.ticket_repo.get(session.selected_ticket_id)
                    response = self._render_psychologists_page(ticket, psychologists, session.pagination_offset)
                return session, response
            
            elif message_lower in ['prev', 'назад', 'предыдущие']:
                session.pagination_offset = max(0, session.pagination_offset - 10)
                ticket = self.ticket_repo.get(session.selected_ticket_id)
                response = self._render_psychologists_page(ticket, psychologists, session.pagination_offset)
                return session, response
            
            else:
                # Пытаемся выбрать психолога по номеру (1-10)
                try:
                    psy_num = int(message.strip())
                    if 1 <= psy_num <= 10:
                        idx = session.pagination_offset + psy_num - 1
                        if idx < len(psychologists):
                            selected_psy = psychologists[idx]
                            # Назначаем заявку психологу
                            success = self.assign_ticket(session.selected_ticket_id, selected_psy.user_id)
                            
                            if success:
                                response = f"✅ Заявка назначена психологу @{selected_psy.username or selected_psy.user_id}"
                            else:
                                response = f"❌ Ошибка при назначении заявки"
                            
                            session.state = State.ADMIN_MENU
                            session.selected_ticket_id = None
                            session.pagination_offset = 0
                            return session, response
                        else:
                            response = "❌ Психолог не найден"
                            return session, response
                except ValueError:
                    pass
                
                response = "❌ Неверный ввод. Введите номер психолога (1-10) или команду (далее/назад/отмена)"
                return session, response
        
        return session, "❌ Неизвестная команда"

    def _handle_psychologist_message(self, session: UserSession, message: str, user_id: str) -> tuple:
        """Обработка сообщений психолога"""
        message_lower = message.strip().lower()
        
        if session.state == State.MENU or message_lower in ['/start', 'start']:
            session.state = State.PSY_MENU
            response = """🧑‍⚕️ *ПАНЕЛЬ ПСИХОЛОГА*

Выберите действие:
1️⃣ Очередь заявок
2️⃣ Мои заявки
3️⃣ Обычное меню

Команды:
/menu - вернуться в обычное меню"""
            return session, response
        
        elif session.state == State.PSY_MENU:
            if message_lower in ['1', 'очередь заявок']:
                session.state = State.PSY_TICKETS_LIST
                tickets = [t for t in self.ticket_repo.get_all() 
                          if t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE)]
                
                if not tickets:
                    response = "✅ Нет заявок в очереди"
                    session.state = State.PSY_MENU
                else:
                    response = "📋 Заявки:\n"
                    for i, t in enumerate(tickets[:5], 1):
                        response += f"\n{i}. {t.id[:8]} - {t.topic} ({t.severity.value})"
                        response += f"\n   От: {t.user_id}"
                
                return session, response
            
            elif message_lower in ['2', 'мои заявки']:
                tickets = [t for t in self.ticket_repo.get_all() 
                          if t.assigned_to == user_id]
                
                if not tickets:
                    response = "Вы не брали в работу ни одну заявку"
                else:
                    response = "📋 Ваши заявки:\n"
                    for t in tickets:
                        response += f"\n• {t.id[:8]} - {t.topic} ({t.status.value})"
                
                return session, response
            
            elif message_lower in ['3', 'обычное меню']:
                session.state = State.MENU
                return session, "Перешли в обычное меню"
        
        # Если психолог в обычной заявке - то же самое
        return self.state_machine.process(session, message)
    def _create_ticket_from_form(self, session: UserSession) -> Ticket:
        """Создание заявки из заполненной формы"""
        form = session.consultation_form
        
        ticket = Ticket(
            id=str(uuid.uuid4()),
            user_id=session.user_id,
            topic=form.topic,
            gender=form.gender,
            age=form.age,
            severity=form.severity,
            message=form.message,
            status=TicketStatus.NEW,
            created_at=datetime.now()
        )
        
        return self.ticket_repo.create(ticket)

    def get_user_tickets(self, user_id: str) -> list[Ticket]:
        """Получение всех заявок пользователя"""
        return self.ticket_repo.get_by_user(user_id)

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Получение заявки по ID"""
        return self.ticket_repo.get(ticket_id)

    def update_ticket_status(self, ticket_id: str, status: TicketStatus) -> bool:
        """Обновление статуса заявки"""
        ticket = self.ticket_repo.get(ticket_id)
        if ticket:
            ticket.status = status
            self.ticket_repo.update(ticket)
            return True
        return False

    def assign_ticket(self, ticket_id: str, specialist_id: str) -> bool:
        """Назначение заявки специалисту"""
        ticket = self.ticket_repo.get(ticket_id)
        if ticket:
            ticket.assigned_to = specialist_id
            ticket.status = TicketStatus.IN_PROGRESS
            self.ticket_repo.update(ticket)
            return True
        return False

    def get_all_tickets(self) -> list[Ticket]:
        """Получение всех заявок (для админов)"""
        return self.ticket_repo.get_all()

    def add_message_to_ticket(self, ticket_id: str, user_id: str, message: str) -> bool:
        """Добавление сообщения в чат заявки"""
        ticket = self.ticket_repo.get(ticket_id)
        if ticket:
            ticket.chat_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "message": message
            })
            self.ticket_repo.update(ticket)
            return True
        return False

    def get_user_role(self, user_id: str) -> UserRole:
        """Получить роль пользователя"""
        return self.role_manager.get_role(user_id)

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Получить профиль пользователя"""
        return self.role_manager.get_user(user_id)

    def promote_to_psychologist(self, user_id: str) -> bool:
        """Повысить до психолога"""
        success = self.role_manager.promote_to_psychologist(user_id)
        if success and self.role_repo:
            updated_profile = self.role_manager.get_user(user_id)
            if updated_profile:
                self.role_repo.save_user(updated_profile)
        return success

    def demote_psychologist(self, user_id: str) -> bool:
        """Понизить психолога"""
        success = self.role_manager.demote_psychologist(user_id)
        if success and self.role_repo:
            updated_profile = self.role_manager.get_user(user_id)
            if updated_profile:
                self.role_repo.save_user(updated_profile)
        return success

    def get_sorted_tickets_for_assignment(self) -> list[Ticket]:
        """Получить заявки для назначения, отсортированные по критичности и дате"""
        severity_order = {"Критическая": 0, "Высокая": 1, "Средняя": 2, "Низкая": 3}
        
        tickets = [t for t in self.ticket_repo.get_all() 
                  if t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE)]
        
        # Сортировка: критичность (убывающая), затем дата (возрастающая)
        tickets.sort(key=lambda t: (
            severity_order.get(t.severity.value, 999),
            t.created_at
        ))
        return tickets

    def get_psychologists_by_workload(self) -> list[UserProfile]:
        """Получить психологов, отсортированных по количеству активных заявок"""
        psychologists = self.role_manager.list_psychologists()
        
        # Подсчитаем активные заявки каждого психолога
        active_statuses = (TicketStatus.NEW, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_RESPONSE)
        workload = {}
        
        for psy in psychologists:
            count = len([t for t in self.ticket_repo.get_all() 
                        if t.assigned_to == psy.user_id and t.status in active_statuses])
            workload[psy.user_id] = count
        
        # Сортируем по количеству активных заявок (меньше - лучше)
        psychologists.sort(key=lambda p: workload.get(p.user_id, 0))
        return psychologists

    def _render_tickets_page(self, tickets: list[Ticket], offset: int) -> str:
        """Рендеринг страницы заявок для выбора"""
        page_tickets = tickets[offset:offset+10]
        total = len(tickets)
        page_num = (offset // 10) + 1
        max_pages = (total + 9) // 10
        
        response = f"📋 *Заявки для назначения (стр. {page_num}/{max_pages})*\n"
        response += f"_Всего: {total}_\n\n"
        
        for i, ticket in enumerate(page_tickets, 1):
            topic = ticket.topic[:30] + "..." if len(ticket.topic) > 30 else ticket.topic
            date_str = ticket.created_at.strftime("%d.%m")
            response += f"{i}. {topic} ({ticket.severity.value}) - {date_str}\n"
        
        response += "\n📍 *Команды:*\n"
        response += "Введите номер заявки (1-10)\n"
        if offset > 0:
            response += "Типовые: `далее` `назад` `отмена`"
        else:
            response += "Типовые: `далее` `отмена`"
        
        return response

    def _render_psychologists_page(self, ticket: Ticket, psychologists: list[UserProfile], offset: int) -> str:
        """Рендеринг страницы психологов для выбора"""
        active_statuses = (TicketStatus.NEW, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_RESPONSE)
        workload = {}
        for psy in psychologists:
            count = len([t for t in self.ticket_repo.get_all() 
                        if t.assigned_to == psy.user_id and t.status in active_statuses])
            workload[psy.user_id] = count
        
        page_psychologists = psychologists[offset:offset+10]
        total = len(psychologists)
        page_num = (offset // 10) + 1
        max_pages = (total + 9) // 10
        
        response = f"👥 *Выберите психолога (стр. {page_num}/{max_pages})*\n\n"
        response += f"📌 *Заявка:* {ticket.topic}\n"
        response += f"   *Критичность:* {ticket.severity.value}\n\n"
        
        response += "*Психологи:*\n"
        for i, psy in enumerate(page_psychologists, 1):
            name_display = f"@{psy.username}" if psy.username else psy.user_id
            load = workload.get(psy.user_id, 0)
            response += f"{i}. {name_display} ({load} активных)\n"
        
        response += "\n📍 *Команды:*\n"
        response += "Введите номер психолога (1-10)\n"
        if offset > 0:
            response += "Типовые: `далее` `назад` `отмена`"
        else:
            response += "Типовые: `далее` `отмена`"
        
        return response

