from typing import Optional
from datetime import datetime
import hashlib
import uuid

from domain.models import UserSession, Ticket, State, TicketStatus
from domain.repositories import SessionRepository, TicketRepository, RoleRepository
from domain.roles import UserRole, RoleManager, UserProfile
from application.state_machine import StateMachine


class BotService:
    """Основной сервис бота, координирующий все операции"""

    @staticmethod
    def _short_ticket_id(ticket_id: str, length: int = 6) -> str:
        """Короткий хеш заявки для отображения в чате"""
        return hashlib.sha256(ticket_id.encode()).hexdigest()[:length].upper()

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
        self.pending_notifications: list[tuple[str, str]] = []  # [(user_id, message), ...]

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
            # Проверяем, есть ли у пользователя активный чат с психологом
            if session.state == State.USER_IN_CHAT and session.active_chat_ticket_id:
                session, response = self._handle_user_in_chat(session, message)
            else:
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
        
        # Обработка глобальных команд
        if message_lower == '/menu':
            session.state = State.MENU
            session.pagination_offset = 0
            session.selected_ticket_id = None
            return session, "Возврат в обычное меню"
        
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
                    response = "👥 *Управление психологами*\n\nПсихологи не назначены\n\n📍 *Действия:*\n1️⃣ Добавить психолога\n2️⃣ Вернуться в меню"
                else:
                    response = "👥 *Управление психологами*\n\n*Текущие психологи:*\n"
                    for psy in psychologists:
                        name = f"{psy.first_name or ''} {psy.last_name or ''}".strip()
                        username = f"@{psy.username}" if psy.username else ""
                        response += f"\n• {psy.user_id} ({username or name or 'нет имени'})"
                    response += "\n\n📍 *Действия:*\n1️⃣ Добавить психолога\n2️⃣ Понизить психолога\n0️⃣ Вернуться в меню"
                
                return session, response
            
            elif message_lower in ['2', 'все заявки']:
                tickets = self.ticket_repo.get_all()
                if not tickets:
                    response = "📋 Заявок нет"
                else:
                    response = "📋 Все заявки:\n"
                    for t in tickets[-10:]:  # Последние 10
                        # Добавляем критичность
                        severity_icon = {
                            "Критическая": "🔴",
                            "Высокая": "🟠",
                            "Средняя": "🟡",
                            "Низкая": "🟢"
                        }.get(t.severity.value, "⚪")
                        
                        # Информация о психологе
                        if t.assigned_to:
                            psychologist = self.role_manager.get_user(t.assigned_to)
                            psy_name = f"@{psychologist.username}" if psychologist and psychologist.username else t.assigned_to
                            psy_info = f" → {psy_name}"
                        else:
                            psy_info = " (не назначен)"
                        
                        response += f"\n{severity_icon} {t.id[:8]} - {t.topic} ({t.status.value}){psy_info}"
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
            message_lower = message.strip().lower()
            
            if message_lower in ['0', 'вернуться в меню', 'назад']:
                session.state = State.ADMIN_MENU
                return session, "Возврат в админ-панель"
            
            elif message_lower in ['1', 'добавить психолога', 'добавить']:
                response = "Отправьте ID или @username пользователя для повышения:"
                session.state = State.ADMIN_PROMOTE_PSYCHO
                return session, response
            
            elif message_lower in ['2', 'понизить психолога', 'понизить']:
                psychologists = self.role_manager.list_psychologists()
                
                if not psychologists:
                    response = "❌ Нет психологов для понижения"
                    session.state = State.ADMIN_MENU
                    return session, response
                
                session.state = State.ADMIN_DEMOTE_PSYCHO_SELECT
                session.pagination_offset = 0
                response = self._render_psychologists_for_demotion(psychologists, 0)
                return session, response
            
            else:
                response = "❌ Неизвестная команда. Выберите действие (1, 2 или 0):"
                return session, response
        
        elif session.state == State.ADMIN_PROMOTE_PSYCHO:
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
        
        elif session.state == State.ADMIN_DEMOTE_PSYCHO_SELECT:
            # Обработка выбора психолога для понижения
            message_lower = message.strip().lower()
            
            psychologists = self.role_manager.list_psychologists()
            
            if message_lower in ['exit', 'отмена', '0']:
                session.state = State.ADMIN_MENU
                response = "Отменено"
                return session, response
            
            elif message_lower in ['next', 'далее', 'следующие']:
                session.pagination_offset += 10
                if session.pagination_offset >= len(psychologists):
                    session.pagination_offset -= 10
                    response = "✅ Это последняя страница"
                else:
                    response = self._render_psychologists_for_demotion(psychologists, session.pagination_offset)
                return session, response
            
            elif message_lower in ['prev', 'назад', 'предыдущие']:
                session.pagination_offset = max(0, session.pagination_offset - 10)
                response = self._render_psychologists_for_demotion(psychologists, session.pagination_offset)
                return session, response
            
            else:
                # Пытаемся выбрать психолога по номеру (1-10)
                try:
                    psy_num = int(message.strip())
                    if 1 <= psy_num <= 10:
                        idx = session.pagination_offset + psy_num - 1
                        if idx < len(psychologists):
                            selected_psy = psychologists[idx]
                            
                            # Понижаем психолога
                            success = self.role_manager.demote_psychologist(selected_psy.user_id)
                            
                            if success:
                                # Сохраняем изменения в БД
                                if self.role_repo:
                                    updated_profile = self.role_manager.get_user(selected_psy.user_id)
                                    if updated_profile:
                                        self.role_repo.save_user(updated_profile)
                                
                                display_name = f"@{selected_psy.username}" if selected_psy.username else selected_psy.user_id
                                response = f"✅ Пользователь {display_name} понижен до обычного пользователя"
                            else:
                                response = f"❌ Ошибка при понижении роли"
                            
                            session.state = State.ADMIN_MENU
                            session.pagination_offset = 0
                            return session, response
                        else:
                            response = "❌ Психолог не найден"
                            return session, response
                except ValueError:
                    pass
                
                response = "❌ Неверный ввод. Введите номер психолога (1-10) или команду (далее/назад/отмена)"
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

    _PSY_MENU_TEXT = """🧑‍⚕️ *ПАНЕЛЬ ПСИХОЛОГА*

Выберите действие:
1️⃣ Очередь заявок
2️⃣ Мои заявки

Команды:
/menu - меню психолога"""

    def _handle_psychologist_message(self, session: UserSession, message: str, user_id: str) -> tuple:
        """Обработка сообщений психолога"""
        message_lower = message.strip().lower()
        
        # Если психолог в режиме чата — обрабатываем до глобальных команд
        if session.state == State.PSY_TICKET_CHAT:
            return self._handle_psy_chat_message(session, message, message_lower, user_id)
        
        # /menu и /start всегда возвращают в панель психолога
        if message_lower in ['/menu', 'menu', '/start', 'start'] or session.state == State.MENU:
            session.state = State.PSY_MENU
            return session, self._PSY_MENU_TEXT
        
        elif session.state == State.PSY_MENU:
            if message_lower in ['1', 'очередь заявок']:
                tickets = [t for t in self.ticket_repo.get_all()
                          if t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE)]
                
                if not tickets:
                    session.state = State.PSY_MENU
                    return session, "✅ Нет заявок в очереди"
                
                session.state = State.PSY_TICKETS_LIST
                session.pagination_offset = 0
                return session, self._render_psy_queue_page(tickets, 0)
            
            elif message_lower in ['2', 'мои заявки']:
                tickets = [t for t in self.ticket_repo.get_all()
                          if t.assigned_to == user_id]
                
                if not tickets:
                    return session, "📋 У вас нет заявок в работе"
                
                session.state = State.PSY_MY_TICKETS
                session.pagination_offset = 0
                return session, self._render_psy_my_tickets_page(tickets, 0)
        
        elif session.state == State.PSY_TICKETS_LIST:
            tickets = [t for t in self.ticket_repo.get_all()
                      if t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE)]
            
            if message_lower in ['exit', 'отмена', '0']:
                session.state = State.PSY_MENU
                return session, self._PSY_MENU_TEXT
            
            elif message_lower in ['next', 'далее', 'следующие']:
                session.pagination_offset += 10
                if session.pagination_offset >= len(tickets):
                    session.pagination_offset -= 10
                    return session, "✅ Это последняя страница"
                return session, self._render_psy_queue_page(tickets, session.pagination_offset)
            
            elif message_lower in ['prev', 'назад', 'предыдущие']:
                session.pagination_offset = max(0, session.pagination_offset - 10)
                return session, self._render_psy_queue_page(tickets, session.pagination_offset)
            
            else:
                try:
                    ticket_num = int(message.strip())
                    if 1 <= ticket_num <= 10:
                        idx = session.pagination_offset + ticket_num - 1
                        if idx < len(tickets):
                            session.selected_ticket_id = tickets[idx].id
                            session.state = State.PSY_TICKET_OPEN
                            return session, self._render_psy_ticket_card(tickets[idx], user_id)
                        return session, "❌ Заявка не найдена"
                except ValueError:
                    pass
                return session, "❌ Введите номер заявки (1-10) или команду (далее/назад/отмена)"
        
        elif session.state == State.PSY_MY_TICKETS:
            tickets = [t for t in self.ticket_repo.get_all()
                      if t.assigned_to == user_id]
            
            if message_lower in ['exit', 'отмена', '0']:
                session.state = State.PSY_MENU
                return session, self._PSY_MENU_TEXT
            
            elif message_lower in ['next', 'далее', 'следующие']:
                session.pagination_offset += 10
                if session.pagination_offset >= len(tickets):
                    session.pagination_offset -= 10
                    return session, "✅ Это последняя страница"
                return session, self._render_psy_my_tickets_page(tickets, session.pagination_offset)
            
            elif message_lower in ['prev', 'назад', 'предыдущие']:
                session.pagination_offset = max(0, session.pagination_offset - 10)
                return session, self._render_psy_my_tickets_page(tickets, session.pagination_offset)
            
            else:
                try:
                    ticket_num = int(message.strip())
                    if 1 <= ticket_num <= 10:
                        idx = session.pagination_offset + ticket_num - 1
                        if idx < len(tickets):
                            session.selected_ticket_id = tickets[idx].id
                            session.state = State.PSY_TICKET_OPEN
                            return session, self._render_psy_ticket_card(tickets[idx], user_id)
                        return session, "❌ Заявка не найдена"
                except ValueError:
                    pass
                return session, "❌ Введите номер заявки (1-10) или команду (далее/назад/отмена)"
        
        elif session.state == State.PSY_TICKET_OPEN:
            ticket = self.ticket_repo.get(session.selected_ticket_id) if session.selected_ticket_id else None
            
            if message_lower in ['0', 'назад', 'назад к списку']:
                # Возвращаемся в тот список, откуда пришли
                if ticket and ticket.assigned_to == user_id:
                    my_tickets = [t for t in self.ticket_repo.get_all() if t.assigned_to == user_id]
                    if my_tickets:
                        session.state = State.PSY_MY_TICKETS
                        session.pagination_offset = 0
                        session.selected_ticket_id = None
                        return session, self._render_psy_my_tickets_page(my_tickets, 0)
                # По умолчанию — в очередь
                queue = [t for t in self.ticket_repo.get_all()
                         if t.status in (TicketStatus.NEW, TicketStatus.WAITING_RESPONSE)]
                if queue:
                    session.state = State.PSY_TICKETS_LIST
                    session.pagination_offset = 0
                    session.selected_ticket_id = None
                    return session, self._render_psy_queue_page(queue, 0)
                session.state = State.PSY_MENU
                session.selected_ticket_id = None
                return session, self._PSY_MENU_TEXT
            
            elif message_lower in ['1', 'взять в работу'] and ticket and ticket.assigned_to != user_id:
                success = self.assign_ticket(session.selected_ticket_id, user_id)
                if success:
                    session.state = State.PSY_MENU
                    session.selected_ticket_id = None
                    return session, f"✅ Заявка взята в работу"
                return session, "❌ Ошибка при назначении заявки"
            
            elif message_lower in ['1', 'изменить статус'] and ticket and ticket.assigned_to == user_id:
                session.state = State.PSY_CHANGE_STATUS
                response = f"📌 *Заявка {ticket.id[:8]}*\n"
                response += f"Текущий статус: {ticket.status.value}\n\n"
                response += "*Выберите новый статус:*\n"
                response += "1️⃣ В работе\n"
                response += "2️⃣ Ожидание ответа\n"
                response += "3️⃣ Закрыто\n"
                response += "0️⃣ Отмена"
                return session, response
            
            elif message_lower in ['2', 'начать чат', 'закрыть чат'] and ticket and ticket.assigned_to == user_id:
                # Проверяем, есть ли активный чат
                client_session = self.session_repo.get(ticket.user_id)
                chat_active = (client_session and client_session.state == State.USER_IN_CHAT 
                              and client_session.active_chat_ticket_id == ticket.id)
                
                if chat_active and message_lower in ['2', 'закрыть чат']:
                    # Закрываем чат
                    client_session.state = State.MENU
                    client_session.active_chat_ticket_id = None
                    self.session_repo.save(client_session)
                    
                    self.pending_notifications.append((
                        ticket.user_id,
                        "💬 *Чат завершён*\n\nПсихолог завершил чат. Спасибо за обращение!\n\nВы возвращены в главное меню."
                    ))
                    
                    session.active_chat_ticket_id = None
                    return session, self._render_psy_ticket_card(ticket, user_id)
                
                elif not chat_active and message_lower in ['2', 'начать чат']:
                    # Начинаем чат — переводим психолога в режим чата
                    session.state = State.PSY_TICKET_CHAT
                    session.active_chat_ticket_id = ticket.id
                    
                    # Переводим пользователя в режим чата
                    if client_session is None:
                        client_session = UserSession(user_id=ticket.user_id, state=State.USER_IN_CHAT)
                    else:
                        client_session.state = State.USER_IN_CHAT
                    client_session.active_chat_ticket_id = ticket.id
                    self.session_repo.save(client_session)
                    
                    # Уведомление пользователю
                    self.pending_notifications.append((
                        ticket.user_id,
                        f"💬 *Чат начат*\n\nПсихолог начал с вами чат по заявке \"{ticket.topic}\".\n\nВаши сообщения будут переданы психологу.\nДля завершения чата напишите /end"
                    ))
                    
                    return session, f"💬 *Чат начат*\n\nВы подключились к чату с пользователем ({ticket.user_id}) по заявке \"{ticket.topic}\".\n\nВаши сообщения будут переданы пользователю.\nДля завершения чата напишите /end"
                
                else:
                    return session, "ℹ️ Действие не соответствует текущему состоянию чата"
            
            else:
                if ticket and ticket.assigned_to == user_id:
                    return session, "❌ Введите номер действия (1-2) или 0 (Назад к списку)"
                return session, "❌ Введите 1 (Взять в работу) или 0 (Назад к списку)"
        
        elif session.state == State.PSY_CHANGE_STATUS:
            ticket = self.ticket_repo.get(session.selected_ticket_id) if session.selected_ticket_id else None
            
            if message_lower in ['0', 'отмена']:
                if ticket:
                    session.state = State.PSY_TICKET_OPEN
                    response = self._render_psy_ticket_card(ticket, user_id)
                    return session, response
                session.state = State.PSY_MENU
                return session, self._PSY_MENU_TEXT
            
            status_map = {
                '1': TicketStatus.IN_PROGRESS,
                'в работе': TicketStatus.IN_PROGRESS,
                '2': TicketStatus.WAITING_RESPONSE,
                'ожидание ответа': TicketStatus.WAITING_RESPONSE,
                '3': TicketStatus.CLOSED,
                'закрыто': TicketStatus.CLOSED,
            }
            
            new_status = status_map.get(message_lower)
            if new_status and ticket:
                self.update_ticket_status(session.selected_ticket_id, new_status)
                session.state = State.PSY_MENU
                session.selected_ticket_id = None
                return session, f"✅ Статус заявки изменён на: {new_status.value}"
            
            return session, "❌ Введите номер статуса (1-3) или 0 (Отмена)"
        
        elif session.state == State.PSY_TICKET_CHAT:
            # Этот блок не должен вызываться — обработка вынесена выше
            return self._handle_psy_chat_message(session, message, message_lower, user_id)
        
        # Если психолог в обычной заявке - то же самое
        return self.state_machine.process(session, message)

    def _handle_psy_chat_message(self, session: UserSession, message: str, message_lower: str, user_id: str) -> tuple:
        """Обработка сообщений психолога в режиме чата"""
        ticket_id = session.active_chat_ticket_id or session.selected_ticket_id
        ticket = self.ticket_repo.get(ticket_id) if ticket_id else None

        if message_lower in ['/end', 'end', '/закрыть чат', 'закрыть чат']:
            # Завершаем чат со стороны психолога
            if ticket:
                client_session = self.session_repo.get(ticket.user_id)
                if client_session and client_session.state == State.USER_IN_CHAT and client_session.active_chat_ticket_id == ticket.id:
                    client_session.state = State.MENU
                    client_session.active_chat_ticket_id = None
                    self.session_repo.save(client_session)

                    self.pending_notifications.append((
                        ticket.user_id,
                        "💬 *Чат завершён*\n\nПсихолог завершил чат. Спасибо за обращение!\n\nВы возвращены в главное меню."
                    ))

            session.state = State.PSY_TICKET_OPEN
            session.active_chat_ticket_id = None
            if ticket:
                return session, f"💬 *Чат завершён*\n\n" + self._render_psy_ticket_card(ticket, user_id)
            return session, "💬 *Чат завершён*"

        elif message_lower in ['/menu', 'menu', '/start', 'start']:
            # /menu и /start тоже завершают чат и возвращают в меню психолога
            if ticket:
                client_session = self.session_repo.get(ticket.user_id)
                if client_session and client_session.state == State.USER_IN_CHAT and client_session.active_chat_ticket_id == ticket.id:
                    client_session.state = State.MENU
                    client_session.active_chat_ticket_id = None
                    self.session_repo.save(client_session)

                    self.pending_notifications.append((
                        ticket.user_id,
                        "💬 *Чат завершён*\n\nПсихолог завершил чат. Спасибо за обращение!\n\nВы возвращены в главное меню."
                    ))

            session.state = State.PSY_MENU
            session.active_chat_ticket_id = None
            session.selected_ticket_id = None
            return session, self._PSY_MENU_TEXT

        else:
            # Пересылаем сообщение пользователю
            if ticket:
                self.add_message_to_ticket(ticket.id, user_id, message)
                self.pending_notifications.append((
                    ticket.user_id,
                    f"💬 *Сообщение от психолога:*\n\n{message}"
                ))
                return session, f"✉️ #{self._short_ticket_id(ticket.id)} Сообщение отправлено"
            return session, "❌ Ошибка: заявка не найдена"

    def _handle_user_in_chat(self, session: UserSession, message: str) -> tuple:
        """Обработка сообщений пользователя в режиме чата с психологом"""
        message_lower = message.strip().lower()
        
        ticket = self.ticket_repo.get(session.active_chat_ticket_id) if session.active_chat_ticket_id else None
        
        if message_lower in ['/end', 'end', '/menu', 'menu']:
            # Пользователь выходит из чата
            psy_id = ticket.assigned_to if ticket else None
            
            if psy_id:
                psy_session = self.session_repo.get(psy_id)
                if psy_session and psy_session.state == State.PSY_TICKET_CHAT and psy_session.active_chat_ticket_id == session.active_chat_ticket_id:
                    psy_session.state = State.PSY_TICKET_OPEN
                    psy_session.active_chat_ticket_id = None
                    self.session_repo.save(psy_session)
                
                self.pending_notifications.append((
                    psy_id,
                    "💬 *Чат завершён*\n\nПользователь завершил чат."
                ))
            
            session.state = State.MENU
            session.active_chat_ticket_id = None
            return session, "💬 *Чат завершён*\n\nВы возвращены в главное меню."
        
        # Пересылаем сообщение психологу
        if ticket and ticket.assigned_to:
            self.add_message_to_ticket(ticket.id, session.user_id, message)
            self.pending_notifications.append((
                ticket.assigned_to,
                f"💬 *Сообщение от пользователя #{self._short_ticket_id(ticket.id)} ({session.user_id}):*\n\n{message}"
            ))
            return session, "✉️ Сообщение отправлено психологу"
        
        # Чат не найден — возвращаем в меню
        session.state = State.MENU
        session.active_chat_ticket_id = None
        return session, "❌ Чат не найден. Вы возвращены в главное меню."

    def get_pending_notifications(self) -> list[tuple[str, str]]:
        """Получить и очистить очередь уведомлений для отправки"""
        notifications = self.pending_notifications.copy()
        self.pending_notifications.clear()
        return notifications

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

    def _render_psy_ticket_card(self, ticket: Ticket, user_id: str) -> str:
        """Рендеринг карточки заявки для психолога"""
        response = f"📌 *Заявка {ticket.id[:8]}*\n\n"
        response += f"Тема: {ticket.topic}\n"
        response += f"Критичность: {ticket.severity.value}\n"
        response += f"Статус: {ticket.status.value}\n"
        response += f"От: {ticket.user_id}\n"
        response += f"\n💬 {ticket.message}\n" if ticket.message else ""
        response += "\n*Действия:*\n"
        if ticket.assigned_to == user_id:
            response += "1️⃣ Изменить статус\n"
            # Проверяем, есть ли активный чат
            user_session = self.session_repo.get(ticket.user_id)
            if user_session and user_session.state == State.USER_IN_CHAT and user_session.active_chat_ticket_id == ticket.id:
                response += "2️⃣ Закрыть чат\n"
            else:
                response += "2️⃣ Начать чат\n"
        else:
            response += "1️⃣ Взять в работу\n"
        response += "0️⃣ Назад к списку"
        return response

    def _render_psy_queue_page(self, tickets: list[Ticket], offset: int) -> str:
        """Рендеринг страницы очереди заявок для психолога"""
        page_tickets = tickets[offset:offset+10]
        total = len(tickets)
        page_num = (offset // 10) + 1
        max_pages = (total + 9) // 10
        
        response = f"📋 *Очередь заявок (стр. {page_num}/{max_pages})*\n"
        response += f"_Всего: {total}_\n\n"
        
        for i, ticket in enumerate(page_tickets, 1):
            topic = ticket.topic[:30] + "..." if len(ticket.topic) > 30 else ticket.topic
            date_str = ticket.created_at.strftime("%d.%m")
            response += f"{i}. {topic} ({ticket.severity.value}) - {date_str}\n"
            response += f"   От: {ticket.user_id}\n"
        
        response += "\n📍 *Команды:*\n"
        response += "Введите номер заявки (1-10)\n"
        if offset > 0:
            response += "Типовые: `далее` `назад` `отмена`"
        else:
            response += "Типовые: `далее` `отмена`"
        
        return response

    def _render_psy_my_tickets_page(self, tickets: list[Ticket], offset: int) -> str:
        """Рендеринг страницы 'Мои заявки' для психолога"""
        page_tickets = tickets[offset:offset+10]
        total = len(tickets)
        page_num = (offset // 10) + 1
        max_pages = (total + 9) // 10
        
        response = f"📋 *Мои заявки (стр. {page_num}/{max_pages})*\n"
        response += f"_Всего: {total}_\n\n"
        
        for i, ticket in enumerate(page_tickets, 1):
            topic = ticket.topic[:30] + "..." if len(ticket.topic) > 30 else ticket.topic
            response += f"{i}. {topic} ({ticket.status.value})\n"
        
        response += "\n📍 *Команды:*\n"
        response += "Введите номер заявки (1-10)\n"
        if offset > 0:
            response += "Типовые: `далее` `назад` `отмена`"
        else:
            response += "Типовые: `далее` `отмена`"
        
        return response

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

    def _render_psychologists_for_demotion(self, psychologists: list[UserProfile], offset: int) -> str:
        """Рендеринг страницы психологов для понижения роли"""
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
        
        response = f"⬇️ *Понижение психолога (стр. {page_num}/{max_pages})*\n\n"
        response += "*Психологи:*\n"
        for i, psy in enumerate(page_psychologists, 1):
            name_display = f"@{psy.username}" if psy.username else psy.user_id
            full_name = f"{psy.first_name or ''} {psy.last_name or ''}".strip()
            load = workload.get(psy.user_id, 0)
            
            response += f"{i}. {name_display}"
            if full_name:
                response += f" ({full_name})"
            response += f" - {load} активных заявок\n"
        
        response += "\n📍 *Команды:*\n"
        response += "Введите номер психолога (1-10) для понижения\n"
        if offset > 0:
            response += "Типовые: `далее` `назад` `отмена`"
        else:
            response += "Типовые: `далее` `отмена`"
        
        return response

