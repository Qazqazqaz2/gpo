"""
API маршруты для приложения GPO My
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from utils.decorators import role_required, json_response, handle_errors
from services import UserService, StudentService, PracticeService, OrganizationService
from utils.exceptions import ValidationError, BusinessLogicError, NotFoundError

api = Blueprint('api', __name__)

# Инициализация сервисов
user_service = UserService()
student_service = StudentService()
practice_service = PracticeService()
organization_service = OrganizationService()


@api.route('/users', methods=['GET'])
@login_required
@role_required('преподаватель', 'администратор')
@json_response
@handle_errors
def get_users():
    """Получить список пользователей"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role_filter = request.args.get('role')
    
    filters = {}
    if role_filter:
        filters['role'] = role_filter
    
    users = user_service.get_paginated(page=page, per_page=per_page, **filters)
    
    return {
        'users': [user.to_dict() for user in users.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': users.total,
            'pages': users.pages,
            'has_next': users.has_next,
            'has_prev': users.has_prev
        }
    }


@api.route('/users/<int:user_id>', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_user(user_id):
    """Получить пользователя по ID"""
    user = user_service.get_by_id(user_id)
    if not user:
        raise NotFoundError("Пользователь не найден", "user", str(user_id))
    
    return user.to_dict()


@api.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@json_response
@handle_errors
def update_user(user_id):
    """Обновить пользователя"""
    data = request.get_json()
    if not data:
        raise ValidationError("Данные не предоставлены")
    
    # Проверяем права доступа
    if current_user.id != user_id and not current_user.has_role('преподаватель'):
        raise BusinessLogicError("Недостаточно прав для изменения этого пользователя")
    
    user = user_service.update_profile(user_id, **data)
    if not user:
        raise NotFoundError("Пользователь не найден", "user", str(user_id))
    
    return user.to_dict()


@api.route('/students', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_students():
    """Получить список студентов"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    group_id = request.args.get('group_id', type=int)
    search = request.args.get('search')
    
    filters = {}
    if group_id:
        filters['group_id'] = group_id
    if search:
        # Поиск по имени
        students = student_service.search_by_name(search)
        return {
            'students': [student.to_dict() for student in students],
            'total': len(students)
        }
    
    students = student_service.get_paginated(page=page, per_page=per_page, **filters)
    
    return {
        'students': [student.to_dict() for student in students.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': students.total,
            'pages': students.pages,
            'has_next': students.has_next,
            'has_prev': students.has_prev
        }
    }


@api.route('/students/<int:student_id>', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_student(student_id):
    """Получить студента по ID"""
    student = student_service.get_student_with_group_info(student_id)
    if not student:
        raise NotFoundError("Студент не найден", "student", str(student_id))
    
    return student


@api.route('/students', methods=['POST'])
@login_required
@role_required('преподаватель', 'администратор')
@json_response
@handle_errors
def create_student():
    """Создать нового студента"""
    data = request.get_json()
    if not data:
        raise ValidationError("Данные не предоставлены")
    
    # Валидация данных
    from utils.validators import Validator
    validation = Validator.validate_student_data(data)
    if not validation['valid']:
        raise ValidationError("Ошибка валидации данных", errors=validation['errors'])
    
    student = student_service.create_student(**data)
    if not student:
        raise BusinessLogicError("Не удалось создать студента")
    
    return student.to_dict(), 201


@api.route('/applications', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_applications():
    """Получить список заявок"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    group_id = request.args.get('group_id', type=int)
    
    # Фильтрация в зависимости от роли
    if current_user.is_student:
        # Студенты видят только свои заявки
        applications = practice_service.get_student_applications(current_user.id)
        return {
            'applications': [practice_service.get_application_with_details(app.id) for app in applications],
            'total': len(applications)
        }
    elif current_user.is_teacher or getattr(current_user, 'is_consultant', False):
        # Преподаватели видят заявки, связанные с ними
        applications = practice_service.get_teacher_applications(current_user.id)
        return {
            'applications': [practice_service.get_application_with_details(app.id) for app in applications],
            'total': len(applications)
        }
    else:
        # Администраторы видят все заявки
        filters = {}
        if status:
            applications = practice_service.get_applications_by_status(status)
        elif group_id:
            applications = practice_service.get_applications_by_group(group_id)
        else:
            applications = practice_service.get_all()
        
        return {
            'applications': [practice_service.get_application_with_details(app.id) for app in applications],
            'total': len(applications)
        }


@api.route('/applications/<int:application_id>', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_application(application_id):
    """Получить заявку по ID"""
    application = practice_service.get_application_with_details(application_id)
    if not application:
        raise NotFoundError("Заявка не найдена", "application", str(application_id))
    
    # Проверяем права доступа
    if current_user.is_student and application['student']['id'] != current_user.id:
        raise BusinessLogicError("Недостаточно прав для просмотра этой заявки")
    
    return application


@api.route('/applications', methods=['POST'])
@login_required
@role_required('студент')
@json_response
@handle_errors
def create_application():
    """Создать новую заявку"""
    data = request.get_json()
    if not data:
        raise ValidationError("Данные не предоставлены")
    
    # Валидация данных
    from utils.validators import Validator
    validation = Validator.validate_application_data(data)
    if not validation['valid']:
        raise ValidationError("Ошибка валидации данных", errors=validation['errors'])
    
    # Получаем студента текущего пользователя
    student = student_service.get_by_id(data.get('student_id'))
    if not student:
        raise NotFoundError("Студент не найден")
    
    # Создаем заявку
    application = practice_service.create_application(
        student_id=student.id,
        practice_type_id=data['practice_type_id'],
        contract_id=data['contract_id'],
        responsible_user_id=current_user.id,
        consultant_leader_id=data['consultant_leader_id'],
        practice_leader_id=data['practice_leader_id'],
        phone_number=data.get('phone_number'),
        email=data.get('email'),
        comments=data.get('comments')
    )
    
    if not application:
        raise BusinessLogicError("Не удалось создать заявку")
    
    return practice_service.get_application_with_details(application.id), 201


@api.route('/applications/<int:application_id>/approve', methods=['POST'])
@login_required
@role_required('преподаватель', 'администратор')
@json_response
@handle_errors
def approve_application(application_id):
    """Одобрить заявку"""
    success = practice_service.approve_application(application_id, current_user.id)
    if not success:
        raise BusinessLogicError("Не удалось одобрить заявку")
    
    return {'message': 'Заявка одобрена'}


@api.route('/applications/<int:application_id>/reject', methods=['POST'])
@login_required
@role_required('преподаватель', 'администратор')
@json_response
@handle_errors
def reject_application(application_id):
    """Отклонить заявку"""
    data = request.get_json() or {}
    reason = data.get('reason')
    
    success = practice_service.reject_application(application_id, current_user.id, reason)
    if not success:
        raise BusinessLogicError("Не удалось отклонить заявку")
    
    return {'message': 'Заявка отклонена'}


@api.route('/organizations', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_organizations():
    """Получить список организаций"""
    organizations = organization_service.get_active_organizations()
    
    return {
        'organizations': [org.to_dict() for org in organizations],
        'total': len(organizations)
    }


@api.route('/organizations/<int:org_id>', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_organization(org_id):
    """Получить организацию по ID"""
    organization = organization_service.get_organization_with_contracts(org_id)
    if not organization:
        raise NotFoundError("Организация не найдена", "organization", str(org_id))
    
    return organization


@api.route('/contracts', methods=['GET'])
@login_required
@json_response
@handle_errors
def get_contracts():
    """Получить список договоров"""
    # Используем OrganizationService для получения договоров
    from services.organization_service import ContractService
    contract_service = ContractService()
    contracts = contract_service.get_available_contracts()
    
    return {
        'contracts': [contract.to_dict() for contract in contracts],
        'total': len(contracts)
    }


@api.route('/statistics', methods=['GET'])
@login_required
@role_required('преподаватель', 'администратор')
@json_response
@handle_errors
def get_statistics():
    """Получить статистику"""
    user_stats = user_service.get_user_stats()
    student_stats = student_service.get_student_stats()
    practice_stats = practice_service.get_statistics()
    
    # Получаем статистику договоров
    from services.organization_service import ContractService
    contract_service = ContractService()
    org_stats = contract_service.get_statistics()
    
    return {
        'users': user_stats,
        'students': student_stats,
        'applications': practice_stats,
        'contracts': org_stats
    }
