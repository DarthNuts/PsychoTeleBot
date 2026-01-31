"""
Тесты для системы ролей (domain/roles.py)
"""
import pytest
from datetime import datetime
from domain.roles import UserRole, UserProfile, RoleManager


class TestUserRole:
    """Тесты для enum UserRole"""
    
    def test_user_role_values(self):
        """Позитивный: проверка значений ролей"""
        assert UserRole.USER.value == "user"
        assert UserRole.PSYCHOLOGIST.value == "psychologist"
        assert UserRole.ADMIN.value == "admin"
    
    def test_user_role_comparison(self):
        """Позитивный: сравнение ролей"""
        assert UserRole.USER == UserRole.USER
        assert UserRole.USER != UserRole.ADMIN
        assert UserRole.PSYCHOLOGIST != UserRole.USER
    
    def test_user_role_string_conversion(self):
        """Позитивный: преобразование в строку"""
        # Enum возвращает полное имя
        assert "USER" in str(UserRole.USER)
        assert "PSYCHOLOGIST" in str(UserRole.PSYCHOLOGIST)
        assert "ADMIN" in str(UserRole.ADMIN)
        # Проверяем value
        assert UserRole.USER.value == "user"
        assert UserRole.PSYCHOLOGIST.value == "psychologist"
        assert UserRole.ADMIN.value == "admin"


class TestUserProfile:
    """Тесты для dataclass UserProfile"""
    
    def test_create_basic_profile(self):
        """Позитивный: создание базового профиля"""
        profile = UserProfile(user_id="123")
        assert profile.user_id == "123"
        assert profile.role == UserRole.USER
        assert profile.username is None
        assert profile.first_name is None
        assert profile.last_name is None
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.updated_at, datetime)
    
    def test_create_full_profile(self):
        """Позитивный: создание полного профиля"""
        now = datetime.now()
        profile = UserProfile(
            user_id="456",
            role=UserRole.PSYCHOLOGIST,
            username="test_user",
            first_name="Иван",
            last_name="Иванов",
            created_at=now,
            updated_at=now
        )
        assert profile.user_id == "456"
        assert profile.role == UserRole.PSYCHOLOGIST
        assert profile.username == "test_user"
        assert profile.first_name == "Иван"
        assert profile.last_name == "Иванов"
        assert profile.created_at == now
        assert profile.updated_at == now
    
    def test_profile_defaults(self):
        """Позитивный: значения по умолчанию"""
        profile = UserProfile(user_id="789")
        assert profile.role == UserRole.USER
        assert profile.created_at <= datetime.now()
        assert profile.updated_at <= datetime.now()
    
    def test_profile_with_empty_strings(self):
        """Граничный: профиль с пустыми строками"""
        profile = UserProfile(
            user_id="999",
            username="",
            first_name="",
            last_name=""
        )
        assert profile.username == ""
        assert profile.first_name == ""
        assert profile.last_name == ""


class TestRoleManager:
    """Тесты для класса RoleManager"""
    
    def test_create_empty_manager(self):
        """Позитивный: создание пустого менеджера"""
        manager = RoleManager()
        assert len(manager.users) == 0
        assert len(manager.admin_ids) == 0
    
    def test_create_manager_with_admins(self):
        """Позитивный: создание менеджера с админами"""
        manager = RoleManager(admin_ids=["111", "222"])
        assert "111" in manager.admin_ids
        assert "222" in manager.admin_ids
    
    def test_get_or_create_new_user(self):
        """Позитивный: создание нового пользователя"""
        manager = RoleManager()
        profile = manager.get_or_create_user("user1")
        
        assert profile.user_id == "user1"
        assert profile.role == UserRole.USER
        assert "user1" in manager.users
    
    def test_get_or_create_existing_user(self):
        """Позитивный: получение существующего пользователя"""
        manager = RoleManager()
        
        # Создаем
        profile1 = manager.get_or_create_user("user2", username="test")
        assert profile1.username == "test"
        
        # Получаем существующего - метаданные НЕ обновляются
        profile2 = manager.get_or_create_user("user2", username="new_name")
        assert profile2.user_id == "user2"
        assert profile2.username == "test"  # Осталась старая
        assert profile1 is profile2  # Тот же объект
    
    def test_get_or_create_with_metadata(self):
        """Позитивный: создание с метаданными"""
        manager = RoleManager()
        profile = manager.get_or_create_user(
            "user3",
            username="ivan_user",
            first_name="Иван",
            last_name="Петров"
        )
        
        assert profile.username == "ivan_user"
        assert profile.first_name == "Иван"
        assert profile.last_name == "Петров"
    
    def test_get_or_create_admin_user(self):
        """Позитивный: админ автоматически получает роль"""
        manager = RoleManager(admin_ids=["admin1"])
        profile = manager.get_or_create_user("admin1")
        
        assert profile.role == UserRole.ADMIN
        assert manager.is_admin("admin1")
    
    def test_promote_to_psychologist_success(self):
        """Позитивный: повышение до психолога"""
        manager = RoleManager()
        manager.get_or_create_user("user4")
        
        result = manager.promote_to_psychologist("user4")
        
        assert result is True
        assert manager.users["user4"].role == UserRole.PSYCHOLOGIST
        assert manager.is_psychologist("user4")
    
    def test_promote_nonexistent_user(self):
        """Негативный: повышение несуществующего пользователя"""
        manager = RoleManager()
        result = manager.promote_to_psychologist("ghost_user")
        
        assert result is False
    
    def test_promote_already_psychologist(self):
        """Граничный: повышение уже психолога"""
        manager = RoleManager()
        manager.get_or_create_user("user5")
        manager.promote_to_psychologist("user5")
        
        # Второе повышение
        result = manager.promote_to_psychologist("user5")
        
        assert result is False
        assert manager.users["user5"].role == UserRole.PSYCHOLOGIST
    
    def test_promote_admin_to_psychologist(self):
        """Негативный: нельзя понизить админа до психолога"""
        manager = RoleManager(admin_ids=["admin2"])
        manager.get_or_create_user("admin2")
        
        result = manager.promote_to_psychologist("admin2")
        
        assert result is False
        assert manager.users["admin2"].role == UserRole.ADMIN
    
    def test_demote_psychologist_success(self):
        """Позитивный: понижение психолога"""
        manager = RoleManager()
        manager.get_or_create_user("user6")
        manager.promote_to_psychologist("user6")
        
        result = manager.demote_psychologist("user6")
        
        assert result is True
        assert manager.users["user6"].role == UserRole.USER
        assert not manager.is_psychologist("user6")
    
    def test_demote_nonexistent_user(self):
        """Негативный: понижение несуществующего пользователя"""
        manager = RoleManager()
        result = manager.demote_psychologist("ghost")
        
        assert result is False
    
    def test_demote_regular_user(self):
        """Граничный: понижение обычного пользователя"""
        manager = RoleManager()
        manager.get_or_create_user("user7")
        
        result = manager.demote_psychologist("user7")
        
        assert result is False
        assert manager.users["user7"].role == UserRole.USER
    
    def test_demote_admin(self):
        """Негативный: нельзя понизить админа"""
        manager = RoleManager(admin_ids=["admin3"])
        manager.get_or_create_user("admin3")
        
        result = manager.demote_psychologist("admin3")
        
        assert result is False
        assert manager.users["admin3"].role == UserRole.ADMIN
    
    def test_is_psychologist_true(self):
        """Позитивный: проверка что пользователь психолог"""
        manager = RoleManager()
        manager.get_or_create_user("user8")
        manager.promote_to_psychologist("user8")
        
        assert manager.is_psychologist("user8") is True
    
    def test_is_psychologist_false(self):
        """Позитивный: проверка что пользователь не психолог"""
        manager = RoleManager()
        manager.get_or_create_user("user9")
        
        assert manager.is_psychologist("user9") is False
    
    def test_is_psychologist_admin(self):
        """Граничный: админ не является психологом"""
        manager = RoleManager(admin_ids=["admin4"])
        manager.get_or_create_user("admin4")
        
        # Админ не психолог (это разные роли)
        assert manager.is_psychologist("admin4") is False
        # Но админ
        assert manager.is_admin("admin4") is True
    
    def test_is_psychologist_nonexistent(self):
        """Негативный: несуществующий пользователь не психолог"""
        manager = RoleManager()
        assert manager.is_psychologist("nobody") is False
    
    def test_is_admin_true(self):
        """Позитивный: проверка что пользователь админ"""
        manager = RoleManager(admin_ids=["admin5"])
        manager.get_or_create_user("admin5")
        
        assert manager.is_admin("admin5") is True
    
    def test_is_admin_false(self):
        """Позитивный: проверка что пользователь не админ"""
        manager = RoleManager()
        manager.get_or_create_user("user10")
        
        assert manager.is_admin("user10") is False
    
    def test_is_admin_without_profile(self):
        """Граничный: админ без созданного профиля"""
        manager = RoleManager(admin_ids=["admin6"])
        
        # Профиль еще не создан, но ID в admin_ids
        assert manager.is_admin("admin6") is True
    
    def test_is_admin_nonexistent(self):
        """Негативный: несуществующий пользователь не админ"""
        manager = RoleManager()
        assert manager.is_admin("nobody") is False
    
    def test_get_role_user(self):
        """Позитивный: получение роли USER"""
        manager = RoleManager()
        manager.get_or_create_user("user11")
        
        assert manager.get_role("user11") == UserRole.USER
    
    def test_get_role_psychologist(self):
        """Позитивный: получение роли PSYCHOLOGIST"""
        manager = RoleManager()
        manager.get_or_create_user("user12")
        manager.promote_to_psychologist("user12")
        
        assert manager.get_role("user12") == UserRole.PSYCHOLOGIST
    
    def test_get_role_admin(self):
        """Позитивный: получение роли ADMIN"""
        manager = RoleManager(admin_ids=["admin7"])
        manager.get_or_create_user("admin7")
        
        assert manager.get_role("admin7") == UserRole.ADMIN
    
    def test_get_role_nonexistent(self):
        """Негативный: роль несуществующего пользователя"""
        manager = RoleManager()
        assert manager.get_role("nobody") == UserRole.USER
    
    def test_get_user_exists(self):
        """Позитивный: получение существующего пользователя"""
        manager = RoleManager()
        created_profile = manager.get_or_create_user("user13")
        
        retrieved_profile = manager.get_user("user13")
        
        assert retrieved_profile is not None
        assert retrieved_profile.user_id == "user13"
        assert retrieved_profile is created_profile
    
    def test_get_user_not_exists(self):
        """Негативный: получение несуществующего пользователя"""
        manager = RoleManager()
        profile = manager.get_user("nobody")
        
        assert profile is None
    
    def test_list_psychologists_empty(self):
        """Позитивный: список психологов пуст"""
        manager = RoleManager()
        manager.get_or_create_user("user14")
        manager.get_or_create_user("user15")
        
        psychologists = manager.list_psychologists()
        
        assert len(psychologists) == 0
    
    def test_list_psychologists_multiple(self):
        """Позитивный: список психологов с несколькими"""
        manager = RoleManager()
        manager.get_or_create_user("user16")
        manager.get_or_create_user("user17")
        manager.get_or_create_user("user18")
        
        manager.promote_to_psychologist("user16")
        manager.promote_to_psychologist("user18")
        
        psychologists = manager.list_psychologists()
        
        assert len(psychologists) == 2
        user_ids = [p.user_id for p in psychologists]
        assert "user16" in user_ids
        assert "user18" in user_ids
        assert "user17" not in user_ids
    
    def test_list_psychologists_excludes_admins(self):
        """Граничный: список психологов не включает админов"""
        manager = RoleManager(admin_ids=["admin8"])
        manager.get_or_create_user("admin8")
        manager.get_or_create_user("user19")
        manager.promote_to_psychologist("user19")
        
        psychologists = manager.list_psychologists()
        
        # Только 1 психолог, админ не включен
        assert len(psychologists) == 1
        assert psychologists[0].user_id == "user19"
        assert psychologists[0].role == UserRole.PSYCHOLOGIST
    
    def test_list_admins_empty(self):
        """Позитивный: список админов пуст"""
        manager = RoleManager()
        admins = manager.list_admins()
        
        assert len(admins) == 0
    
    def test_list_admins_multiple(self):
        """Позитивный: список админов с несколькими"""
        manager = RoleManager(admin_ids=["admin9", "admin10"])
        manager.get_or_create_user("admin9")
        manager.get_or_create_user("admin10")
        
        admins = manager.list_admins()
        
        assert len(admins) == 2
        admin_ids = [a.user_id for a in admins]
        assert "admin9" in admin_ids
        assert "admin10" in admin_ids
    
    def test_list_admins_only_created(self):
        """Граничный: список админов только с созданными профилями"""
        manager = RoleManager(admin_ids=["admin11", "admin12", "admin13"])
        manager.get_or_create_user("admin11")
        # admin12 и admin13 не создали профиль
        
        admins = manager.list_admins()
        
        # Только созданный админ в списке
        assert len(admins) == 1
        assert admins[0].user_id == "admin11"
    
    def test_multiple_operations_sequence(self):
        """Интеграционный: последовательность операций"""
        manager = RoleManager(admin_ids=["boss"])
        
        # Создаем пользователей
        manager.get_or_create_user("boss")
        manager.get_or_create_user("doc1")
        manager.get_or_create_user("doc2")
        manager.get_or_create_user("patient1")
        
        # Назначаем психологов
        manager.promote_to_psychologist("doc1")
        manager.promote_to_psychologist("doc2")
        
        # Проверяем роли
        assert manager.is_admin("boss")
        assert manager.is_psychologist("doc1")
        assert manager.is_psychologist("doc2")
        assert not manager.is_psychologist("patient1")
        # Админ не психолог
        assert not manager.is_psychologist("boss")
        
        # Понижаем одного психолога
        manager.demote_psychologist("doc2")
        
        # Финальные проверки
        psychologists = manager.list_psychologists()
        # Только doc1, без boss (admin)
        assert len(psychologists) == 1
        assert psychologists[0].user_id == "doc1"
        
        admins = manager.list_admins()
        assert len(admins) == 1
        assert admins[0].user_id == "boss"
    
    def test_role_persistence_simulation(self):
        """Интеграционный: симуляция персистентности"""
        # Создаем менеджер с данными
        manager1 = RoleManager(admin_ids=["super_admin"])
        manager1.get_or_create_user("super_admin")
        manager1.get_or_create_user("psycho1")
        manager1.promote_to_psychologist("psycho1")
        
        # Экспортируем пользователей
        users_data = list(manager1.users.values())
        
        # "Перезагружаем" - создаем новый менеджер
        manager2 = RoleManager(admin_ids=["super_admin"])
        
        # Загружаем пользователей
        for user in users_data:
            manager2.users[user.user_id] = user
        
        # Проверяем что роли сохранились
        assert manager2.is_admin("super_admin")
        assert manager2.is_psychologist("psycho1")
        assert manager2.get_role("super_admin") == UserRole.ADMIN
        assert manager2.get_role("psycho1") == UserRole.PSYCHOLOGIST


class TestRoleManagerEdgeCases:
    """Граничные и специальные случаи"""
    
    def test_empty_user_id(self):
        """Граничный: пустой user_id"""
        manager = RoleManager()
        profile = manager.get_or_create_user("")
        
        assert profile.user_id == ""
        assert "" in manager.users
    
    def test_very_long_user_id(self):
        """Граничный: очень длинный user_id"""
        long_id = "x" * 1000
        manager = RoleManager()
        profile = manager.get_or_create_user(long_id)
        
        assert profile.user_id == long_id
    
    def test_special_characters_in_id(self):
        """Граничный: специальные символы в ID"""
        special_id = "user-123_abc@test.com"
        manager = RoleManager()
        profile = manager.get_or_create_user(special_id)
        
        assert profile.user_id == special_id
    
    def test_unicode_in_metadata(self):
        """Граничный: Unicode в метаданных"""
        manager = RoleManager()
        profile = manager.get_or_create_user(
            "user_unicode",
            username="тест_пользователь",
            first_name="Иван",
            last_name="测试"
        )
        
        assert profile.username == "тест_пользователь"
        assert profile.first_name == "Иван"
        assert profile.last_name == "测试"
    
    def test_none_values_in_admin_ids(self):
        """Граничный: None в списке админов"""
        manager = RoleManager(admin_ids=None)
        assert len(manager.admin_ids) == 0
    
    def test_duplicate_admin_ids(self):
        """Граничный: дубликаты в admin_ids"""
        manager = RoleManager(admin_ids=["admin1", "admin1", "admin2"])
        
        # Set должен убрать дубликаты
        assert len(manager.admin_ids) == 2
    
    def test_role_change_updates_profile(self):
        """Интеграционный: изменение роли обновляет профиль"""
        manager = RoleManager()
        profile = manager.get_or_create_user("changing_user")
        
        original_updated_at = profile.updated_at
        
        # Небольшая задержка
        import time
        time.sleep(0.01)
        
        # Повышаем
        manager.promote_to_psychologist("changing_user")
        
        # updated_at должен обновиться
        assert profile.updated_at > original_updated_at
        assert profile.role == UserRole.PSYCHOLOGIST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
