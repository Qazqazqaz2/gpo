"""
Модели приложения GPO My
Инициализация всех моделей и связей
"""
from .base import BaseModel
from .user import User, Role
from .academic import Student, Group, Direction, Cafedral, PracticTime, ConsultantGroup
from .practice import PracticeType, AskForm, Status, PracticeDiary
from .organization import Organization, Contract
from .template import Field, Template

__all__ = [
    'BaseModel',
    'User', 'Role',
    'Student', 'Group', 'Direction', 'Cafedral', 'PracticTime', 'ConsultantGroup',
    'PracticeType', 'AskForm', 'Status', 'PracticeDiary',
    'Organization', 'Contract',
    'Field', 'Template'
]







