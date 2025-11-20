"""
Сервис для работы с пользователями
"""
from typing import Optional, List
from werkzeug.security import generate_password_hash, check_password_hash
from .base_service import BaseService
from models.user import User, Role
from extensions import db


class UserService(BaseService):
    """Сервис для работы с пользователями"""
    
    def __init__(self):
        super().__init__(User)
    
    def create_user(self, username: str, password: str, email: str = None, 
                   role_name: str = 'студент') -> Optional[User]:
        """Создать нового пользователя"""
        try:
            # Проверяем, не существует ли уже пользователь
            if self.get_by_username(username):
                raise ValueError(f"Пользователь с именем {username} уже существует")
            
            if email and self.get_by_email(email):
                raise ValueError(f"Пользователь с email {email} уже существует")
            
            # Получаем роль
            role = Role.get_by_name(role_name)
            if not role:
                # Создаем роль, если её нет
                role = Role(name=role_name)
                role.save()
            
            # Создаем пользователя
            user = User(
                username=username,
                email=email,
                role_id=role.id
            )
            user.set_password(password)
            user.save()
            
            return user
        except Exception as e:
            db.session.rollback()
            raise e
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        user = self.get_by_username(username)
        if user and user.check_password(password) and user.is_active:
            return user
        return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени"""
        return User.get_by_username(username)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        return User.get_by_email(email)
    
    def get_by_role(self, role_name: str) -> List[User]:
        """Получить пользователей по роли"""
        return User.get_by_role(role_name)
    
    def get_teachers(self) -> List[User]:
        """Получить всех преподавателей"""
        return self.get_by_role('преподаватель')
    
    def get_consultants(self) -> List[User]:
        """Получить всех преподавателей-консультантов"""
        return self.get_by_role('преподаватель консультант')
    
    def get_students(self) -> List[User]:
        """Получить всех студентов"""
        return self.get_by_role('студент')
    
    def update_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Обновить пароль пользователя"""
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False
            
            if not user.check_password(old_password):
                raise ValueError("Неверный текущий пароль")
            
            user.set_password(new_password)
            user.save()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def update_profile(self, user_id: int, **kwargs) -> Optional[User]:
        """Обновить профиль пользователя"""
        try:
            user = self.get_by_id(user_id)
            if not user:
                return None
            
            # Проверяем уникальность email, если он изменяется
            if 'email' in kwargs and kwargs['email']:
                existing_user = self.get_by_email(kwargs['email'])
                if existing_user and existing_user.id != user_id:
                    raise ValueError(f"Пользователь с email {kwargs['email']} уже существует")
            
            # Проверяем уникальность username, если он изменяется
            if 'username' in kwargs and kwargs['username']:
                existing_user = self.get_by_username(kwargs['username'])
                if existing_user and existing_user.id != user_id:
                    raise ValueError(f"Пользователь с именем {kwargs['username']} уже существует")
            
            user.update(**kwargs)
            return user
        except Exception as e:
            db.session.rollback()
            raise e
    
    def deactivate_user(self, user_id: int) -> bool:
        """Деактивировать пользователя"""
        try:
            user = self.get_by_id(user_id)
            if user:
                user.update(is_active=False)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    def activate_user(self, user_id: int) -> bool:
        """Активировать пользователя"""
        try:
            user = self.get_by_id(user_id)
            if user:
                user.update(is_active=True)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    def change_role(self, user_id: int, role_name: str) -> bool:
        """Изменить роль пользователя"""
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False
            
            role = Role.get_by_name(role_name)
            if not role:
                # Создаем роль, если её нет
                role = Role(name=role_name)
                role.save()
            
            user.update(role_id=role.id)
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_user_stats(self) -> dict:
        """Получить статистику пользователей"""
        total_users = self.count()
        active_users = self.count(is_active=True)
        teachers = len(self.get_teachers())
        students = len(self.get_students())
        consultants = len(self.get_consultants())
        
        return {
            'total': total_users,
            'active': active_users,
            'teachers': teachers,
            'students': students,
            'consultants': consultants,
            'inactive': total_users - active_users
        }







