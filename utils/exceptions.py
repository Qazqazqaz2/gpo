"""
Пользовательские исключения
"""


class ValidationError(Exception):
    """Ошибка валидации данных"""
    
    def __init__(self, message: str, field: str = None, errors: list = None):
        self.message = message
        self.field = field
        self.errors = errors or []
        super().__init__(self.message)


class BusinessLogicError(Exception):
    """Ошибка бизнес-логики"""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(Exception):
    """Ошибка - объект не найден"""
    
    def __init__(self, message: str, object_type: str = None, object_id: str = None):
        self.message = message
        self.object_type = object_type
        self.object_id = object_id
        super().__init__(self.message)


class PermissionError(Exception):
    """Ошибка прав доступа"""
    
    def __init__(self, message: str, required_permission: str = None):
        self.message = message
        self.required_permission = required_permission
        super().__init__(self.message)


class DuplicateError(Exception):
    """Ошибка дублирования"""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class ConfigurationError(Exception):
    """Ошибка конфигурации"""
    
    def __init__(self, message: str, setting: str = None):
        self.message = message
        self.setting = setting
        super().__init__(self.message)


class ExternalServiceError(Exception):
    """Ошибка внешнего сервиса"""
    
    def __init__(self, message: str, service: str = None, status_code: int = None):
        self.message = message
        self.service = service
        self.status_code = status_code
        super().__init__(self.message)













