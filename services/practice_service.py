"""
Сервис для работы с практикой и заявками
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_service import BaseService
from models.practice import AskForm, PracticeType, Status
from models.academic import Student, Group
from models.user import User
from models.organization import Contract
from extensions import db


class PracticeService(BaseService):
    """Сервис для работы с практикой"""
    
    def __init__(self):
        super().__init__(AskForm)
    
    def create_application(self, student_id: int, practice_type_id: int, 
                         contract_id: int, responsible_user_id: int,
                         consultant_leader_id: int, practice_leader_id: int,
                         phone_number: str = None, email: str = None,
                         comments: str = None) -> Optional[AskForm]:
        """Создать заявку на практику"""
        try:
            # Проверяем существование связанных объектов
            student = Student.get_by_id(student_id)
            if not student:
                raise ValueError("Студент не найден")
            
            practice_type = PracticeType.get_by_id(practice_type_id)
            if not practice_type:
                raise ValueError("Тип практики не найден")
            
            contract = Contract.get_by_id(contract_id)
            if not contract:
                raise ValueError("Договор не найден")
            
            # Проверяем доступность слотов в договоре
            if not contract.has_available_slots():
                raise ValueError("В договоре нет доступных слотов")
            
            # Получаем статус "На рассмотрении"
            status = Status.get_by_name('0')
            if not status:
                # Создаем статусы по умолчанию
                Status.create_default_statuses()
                status = Status.get_by_name('0')
            
            # Создаем заявку
            ask_form = AskForm(
                student_id=student_id,
                practice_type_id=practice_type_id,
                group_id=student.group_id,
                contract_id=contract_id,
                responsible_user_id=responsible_user_id,
                consultant_leader_id=consultant_leader_id,
                practice_leader_id=practice_leader_id,
                status_id=status.id,
                phone_number=phone_number,
                email=email,
                comments=comments
            )
            ask_form.save()
            
            return ask_form
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_student_applications(self, student_id: int) -> List[AskForm]:
        """Получить заявки студента"""
        return AskForm.get_by_student(student_id)
    
    def get_pending_applications(self) -> List[AskForm]:
        """Получить заявки на рассмотрении"""
        return AskForm.get_pending()
    
    def get_approved_applications(self) -> List[AskForm]:
        """Получить одобренные заявки"""
        return AskForm.get_approved()
    
    def get_applications_by_group(self, group_id: int) -> List[AskForm]:
        """Получить заявки группы"""
        return AskForm.get_by_group(group_id)
    
    def get_applications_by_status(self, status_name: str) -> List[AskForm]:
        """Получить заявки по статусу"""
        return AskForm.get_by_status(status_name)
    
    def approve_application(self, application_id: int, approver_id: int) -> bool:
        """Одобрить заявку"""
        try:
            application = self.get_by_id(application_id)
            if not application:
                return False
            
            # Проверяем права на одобрение
            approver = User.get_by_id(approver_id)
            if not approver or not approver.is_teacher:
                raise ValueError("Недостаточно прав для одобрения заявки")
            
            application.approve()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def reject_application(self, application_id: int, rejector_id: int, reason: str = None) -> bool:
        """Отклонить заявку"""
        try:
            application = self.get_by_id(application_id)
            if not application:
                return False
            
            # Проверяем права на отклонение
            rejector = User.get_by_id(rejector_id)
            if not rejector or not rejector.is_teacher:
                raise ValueError("Недостаточно прав для отклонения заявки")
            
            application.reject()
            
            # Добавляем причину отклонения в комментарии
            if reason:
                current_comments = application.comments or ""
                application.update(comments=f"{current_comments}\nПричина отклонения: {reason}")
            
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def set_in_progress(self, application_id: int) -> bool:
        """Установить статус "В процессе" """
        try:
            application = self.get_by_id(application_id)
            if not application:
                return False
            
            application.set_in_progress()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_application_with_details(self, application_id: int) -> Optional[Dict[str, Any]]:
        """Получить заявку с подробной информацией"""
        application = self.get_by_id(application_id)
        if not application:
            return None
        
        return {
            'id': application.id,
            'student': {
                'id': application.student.id,
                'full_name': application.student.full_name,
                'group': application.student.group.name if application.student.group else None
            },
            'practice_type': {
                'id': application.practice_type.id,
                'name': application.practice_type.name
            },
            'contract': {
                'id': application.contract.id,
                'number': application.contract.contract_number,
                'organization': application.contract.organization.name
            },
            'responsible_user': {
                'id': application.responsible_user.id,
                'username': application.responsible_user.username
            },
            'consultant_leader': {
                'id': application.consultant_user.id,
                'username': application.consultant_user.username
            },
            'practice_leader': {
                'id': application.practice_leader_user.id,
                'username': application.practice_leader_user.username
            },
            'status': {
                'id': application.status.id,
                'name': application.status.name,
                'description': application.status.description,
                'color': application.status.color
            },
            'phone_number': application.phone_number,
            'email': application.email,
            'comments': application.comments,
            'consultant_contract_signature': application.consultant_contract_signature,
            'consultant_contract_signed_at': application.consultant_contract_signed_at,
            'consultant_application_signature': application.consultant_application_signature,
            'consultant_application_signed_at': application.consultant_application_signed_at,
            'created_at': application.created_at,
            'updated_at': application.updated_at
        }
    
    def get_teacher_applications(self, teacher_id: int) -> List[AskForm]:
        """Получить заявки, связанные с преподавателем"""
        return AskForm.query.filter(
            (AskForm.consultant_leader_id == teacher_id) |
            (AskForm.practice_leader_id == teacher_id)
        ).all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику заявок"""
        total_applications = self.count()
        pending = len(self.get_pending_applications())
        approved = len(self.get_approved_applications())
        rejected = len(self.get_applications_by_status('3'))
        in_progress = len(self.get_applications_by_status('1'))
        
        # Статистика по типам практики
        practice_types = PracticeType.get_all()
        practice_stats = []
        for practice_type in practice_types:
            count = AskForm.query.filter_by(practice_type_id=practice_type.id).count()
            practice_stats.append({
                'name': practice_type.name,
                'count': count
            })
        
        # Статистика по группам
        groups = Group.get_all()
        group_stats = []
        for group in groups:
            count = AskForm.query.filter_by(group_id=group.id).count()
            group_stats.append({
                'name': group.name,
                'count': count
            })
        
        return {
            'total': total_applications,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'in_progress': in_progress,
            'practice_types': practice_stats,
            'groups': group_stats
        }
    
    def search_applications(self, query: str) -> List[AskForm]:
        """Поиск заявок"""
        return AskForm.query.join(Student).filter(
            Student.name.ilike(f'%{query}%') |
            Student.surname.ilike(f'%{query}%') |
            Student.patronymic.ilike(f'%{query}%')
        ).all()







