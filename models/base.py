"""
Базовая модель с общими полями и методами
"""
from datetime import datetime
from extensions import db


class BaseModel(db.Model):
    """Базовая модель с общими полями"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def save(self):
        """Сохранить объект в базу данных"""
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def delete(self):
        """Удалить объект из базы данных"""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def update(self, **kwargs):
        """Обновить поля объекта"""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def to_dict(self):
        """Преобразовать объект в словарь"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def get_by_id(cls, id):
        """Получить объект по ID"""
        return cls.query.get(id)
    
    @classmethod
    def get_all(cls):
        """Получить все объекты"""
        return cls.query.all()
    
    @classmethod
    def get_paginated(cls, page=1, per_page=20):
        """Получить объекты с пагинацией"""
        return cls.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )













