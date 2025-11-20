"""
Валидаторы для приложения
"""
import re
from typing import Any, Optional, List, Dict
from datetime import datetime
from werkzeug.security import generate_password_hash


class Validator:
    """Класс для валидации данных"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Валидация email адреса"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Валидация номера телефона"""
        if not phone:
            return False
        
        # Убираем все нецифровые символы
        digits = re.sub(r'\D', '', phone)
        
        # Проверяем длину (должно быть 10-11 цифр)
        return 10 <= len(digits) <= 11
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Валидация пароля"""
        result = {
            'valid': True,
            'errors': [],
            'strength': 'weak'
        }
        
        if not password:
            result['valid'] = False
            result['errors'].append('Пароль не может быть пустым')
            return result
        
        if len(password) < 8:
            result['valid'] = False
            result['errors'].append('Пароль должен содержать минимум 8 символов')
        
        if not re.search(r'[A-Z]', password):
            result['errors'].append('Пароль должен содержать заглавные буквы')
        
        if not re.search(r'[a-z]', password):
            result['errors'].append('Пароль должен содержать строчные буквы')
        
        if not re.search(r'\d', password):
            result['errors'].append('Пароль должен содержать цифры')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result['errors'].append('Пароль должен содержать специальные символы')
        
        # Определяем силу пароля
        if len(result['errors']) == 0:
            result['strength'] = 'strong'
        elif len(result['errors']) <= 2:
            result['strength'] = 'medium'
        else:
            result['strength'] = 'weak'
        
        if result['errors']:
            result['valid'] = False
        
        return result
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """Валидация имени пользователя"""
        result = {
            'valid': True,
            'errors': []
        }
        
        if not username:
            result['valid'] = False
            result['errors'].append('Имя пользователя не может быть пустым')
            return result
        
        if len(username) < 3:
            result['valid'] = False
            result['errors'].append('Имя пользователя должно содержать минимум 3 символа')
        
        if len(username) > 50:
            result['valid'] = False
            result['errors'].append('Имя пользователя не должно превышать 50 символов')
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            result['valid'] = False
            result['errors'].append('Имя пользователя может содержать только буквы, цифры, точки, дефисы и подчеркивания')
        
        return result
    
    @staticmethod
    def validate_date(date_string: str, format: str = '%d.%m.%Y') -> bool:
        """Валидация даты"""
        try:
            datetime.strptime(date_string, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Валидация обязательных полей"""
        result = {
            'valid': True,
            'errors': [],
            'missing_fields': []
        }
        
        for field in required_fields:
            if field not in data or not data[field]:
                result['valid'] = False
                result['missing_fields'].append(field)
                result['errors'].append(f'Поле {field} обязательно для заполнения')
        
        return result
    
    @staticmethod
    def validate_student_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных студента"""
        result = {
            'valid': True,
            'errors': []
        }
        
        # Проверяем обязательные поля
        required_fields = ['name', 'surname', 'group_id']
        required_validation = Validator.validate_required_fields(data, required_fields)
        
        if not required_validation['valid']:
            result['valid'] = False
            result['errors'].extend(required_validation['errors'])
        
        # Проверяем email, если указан
        if 'email' in data and data['email']:
            if not Validator.validate_email(data['email']):
                result['valid'] = False
                result['errors'].append('Некорректный email адрес')
        
        # Проверяем телефон, если указан
        if 'phone' in data and data['phone']:
            if not Validator.validate_phone(data['phone']):
                result['valid'] = False
                result['errors'].append('Некорректный номер телефона')
        
        return result
    
    @staticmethod
    def validate_application_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных заявки на практику"""
        result = {
            'valid': True,
            'errors': []
        }
        
        # Проверяем обязательные поля
        required_fields = ['student_id', 'practice_type_id', 'contract_id', 
                          'consultant_leader_id', 'practice_leader_id']
        required_validation = Validator.validate_required_fields(data, required_fields)
        
        if not required_validation['valid']:
            result['valid'] = False
            result['errors'].extend(required_validation['errors'])
        
        # Проверяем email, если указан
        if 'email' in data and data['email']:
            if not Validator.validate_email(data['email']):
                result['valid'] = False
                result['errors'].append('Некорректный email адрес')
        
        # Проверяем телефон, если указан
        if 'phone_number' in data and data['phone_number']:
            if not Validator.validate_phone(data['phone_number']):
                result['valid'] = False
                result['errors'].append('Некорректный номер телефона')
        
        return result
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Очистка строки от потенциально опасных символов"""
        if not value:
            return ''
        
        # Убираем HTML теги
        value = re.sub(r'<[^>]+>', '', value)
        
        # Убираем лишние пробелы
        value = ' '.join(value.split())
        
        return value.strip()
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """Валидация расширения файла"""
        if not filename:
            return False
        
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return extension in [ext.lower() for ext in allowed_extensions]
    
    @staticmethod
    def validate_file_size(file_size: int, max_size: int) -> bool:
        """Валидация размера файла"""
        return file_size <= max_size

