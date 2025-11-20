"""
Модели шаблонов и полей
"""
from .base import BaseModel
from extensions import db


class Field(BaseModel):
    """Модель поля шаблона"""
    __tablename__ = 'fields'
    
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    type = db.Column(db.String(35), nullable=False)  # text, number, date, email, etc.
    block = db.Column(db.String(255), nullable=True)
    page = db.Column(db.String(255), nullable=True)
    text = db.Column(db.Text, nullable=True)
    mutability = db.Column(db.String(255), nullable=True)
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    validation_rules = db.Column(db.JSON, nullable=True)  # JSON для правил валидации
    
    @classmethod
    def get_by_name(cls, name):
        """Получить поле по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_by_type(cls, field_type):
        """Получить поля по типу"""
        return cls.query.filter_by(type=field_type).all()
    
    @classmethod
    def get_by_block(cls, block):
        """Получить поля по блоку"""
        return cls.query.filter_by(block=block).all()
    
    def validate_value(self, value):
        """Валидировать значение поля"""
        if self.is_required and not value:
            return False, f"Поле {self.name} обязательно для заполнения"
        
        if not value:  # Если поле не обязательное и пустое
            return True, None
        
        # Базовая валидация по типу
        if self.type == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False, f"Некорректный email в поле {self.name}"
        
        elif self.type == 'number':
            try:
                float(value)
            except ValueError:
                return False, f"Поле {self.name} должно содержать число"
        
        elif self.type == 'date':
            try:
                from datetime import datetime
                datetime.strptime(value, '%d.%m.%Y')
            except ValueError:
                return False, f"Поле {self.name} должно содержать дату в формате ДД.ММ.ГГГГ"
        
        return True, None
    
    def __repr__(self):
        return f'<Field {self.name}>'


class Template(BaseModel):
    """Модель шаблона документа"""
    __tablename__ = 'templates'
    
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    template_body = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    template_type = db.Column(db.String(50), nullable=False, default='docx')  # docx, pdf, html
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    version = db.Column(db.String(20), nullable=True)
    
    @classmethod
    def get_by_name(cls, name):
        """Получить шаблон по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_active(cls):
        """Получить активные шаблоны"""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_by_type(cls, template_type):
        """Получить шаблоны по типу"""
        return cls.query.filter_by(template_type=template_type, is_active=True).all()
    
    def get_fields(self):
        """Получить поля шаблона"""
        # Парсинг полей из template_body
        import re
        field_pattern = r'\[([A-Z_]+)\]'
        fields = re.findall(field_pattern, self.template_body)
        return list(set(fields))  # Убираем дубликаты
    
    def fill_template(self, data):
        """Заполнить шаблон данными"""
        filled_body = self.template_body
        for key, value in data.items():
            placeholder = f'[{key}]'
            filled_body = filled_body.replace(placeholder, str(value))
        return filled_body
    
    def validate_data(self, data):
        """Валидировать данные для заполнения шаблона"""
        required_fields = self.get_fields()
        missing_fields = []
        
        for field_name in required_fields:
            if field_name not in data or not data[field_name]:
                missing_fields.append(field_name)
        
        if missing_fields:
            return False, f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
        
        return True, None
    
    def __repr__(self):
        return f'<Template {self.name}>'
