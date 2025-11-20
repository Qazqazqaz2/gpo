"""
Сервисы приложения GPO My
Слой бизнес-логики
"""
from .user_service import UserService
from .student_service import StudentService
from .practice_service import PracticeService
from .organization_service import OrganizationService
from .pdf_service import PDFService
from .email_service import EmailService

__all__ = [
    'UserService',
    'StudentService', 
    'PracticeService',
    'OrganizationService',
    'PDFService',
    'EmailService'
]













