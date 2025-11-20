"""
Модели пользователей и ролей
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .base import BaseModel
from extensions import db


class User(UserMixin, BaseModel):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    
    # Relationships
    role = db.relationship("Role", back_populates="users")
    responsible_forms = db.relationship("AskForm", foreign_keys="AskForm.responsible_user_id", 
                                      back_populates="responsible_user")
    consultant_forms = db.relationship("AskForm", foreign_keys="AskForm.consultant_leader_id", 
                                      back_populates="consultant_user")
    practice_leader_forms = db.relationship("AskForm", foreign_keys="AskForm.practice_leader_id", 
                                           back_populates="practice_leader_user")
    consultant_groups = db.relationship("ConsultantGroup", back_populates="consultant", cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Проверить пароль"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def roles(self):
        """Получить роли пользователя"""
        if self.role:
            return [self.role.name]
        return []
    
    @property
    def is_student(self):
        """Проверить, является ли пользователь студентом"""
        return 'студент' in self.roles
    
    @property
    def is_teacher(self):
        """Проверить, является ли пользователь преподавателем"""
        return 'преподаватель' in self.roles
    
    @property
    def is_consultant(self):
        """Проверить, является ли пользователь преподавателем-консультантом"""
        return 'преподаватель консультант' in self.roles
    
    def has_role(self, role_name):
        """Проверить, имеет ли пользователь определенную роль"""
        return role_name in self.roles
    
    @classmethod
    def get_by_username(cls, username):
        """Получить пользователя по имени"""
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def get_by_email(cls, email):
        """Получить пользователя по email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_by_role(cls, role_name):
        """Получить пользователей по роли"""
        return cls.query.join(Role).filter(Role.name == role_name).all()
    
    def __repr__(self):
        return f'<User {self.username}>'


class Role(BaseModel):
    """Модель роли"""
    __tablename__ = 'roles'
    
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    permissions = db.Column(db.JSON, nullable=True)  # JSON для хранения разрешений
    
    # Relationships
    users = db.relationship("User", back_populates="role")
    
    @classmethod
    def get_by_name(cls, name):
        """Получить роль по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def create_default_roles(cls):
        """Создать роли по умолчанию"""
        default_roles = [
            {'name': 'студент', 'description': 'Студент', 'permissions': ['view_own_forms', 'create_form']},
            {'name': 'преподаватель', 'description': 'Преподаватель', 'permissions': ['view_all_forms', 'approve_forms', 'manage_students']},
            {'name': 'преподаватель консультант', 'description': 'Преподаватель-консультант', 'permissions': ['view_assigned_forms', 'sign_documents']},
            {'name': 'администратор', 'description': 'Администратор', 'permissions': ['full_access']}
        ]
        
        for role_data in default_roles:
            existing_role = cls.get_by_name(role_data['name'])
            if not existing_role:
                role = cls(**role_data)
                role.save()
    
    def has_permission(self, permission):
        """Проверить, имеет ли роль определенное разрешение"""
        if not self.permissions:
            return False
        return permission in self.permissions
    
    def __repr__(self):
        return f'<Role {self.name}>'
