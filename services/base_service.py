"""
Базовый сервис с общими методами
"""
from typing import Optional, List, Dict, Any
from extensions import db
from models.base import BaseModel


class BaseService:
    """Базовый класс для всех сервисов"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def create(self, **kwargs) -> BaseModel:
        """Создать новый объект"""
        try:
            obj = self.model_class(**kwargs)
            obj.save()
            return obj
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_by_id(self, obj_id: int) -> Optional[BaseModel]:
        """Получить объект по ID"""
        return self.model_class.get_by_id(obj_id)
    
    def get_all(self) -> List[BaseModel]:
        """Получить все объекты"""
        return self.model_class.get_all()
    
    def update(self, obj_id: int, **kwargs) -> Optional[BaseModel]:
        """Обновить объект"""
        try:
            obj = self.get_by_id(obj_id)
            if obj:
                obj.update(**kwargs)
                return obj
            return None
        except Exception as e:
            db.session.rollback()
            raise e
    
    def delete(self, obj_id: int) -> bool:
        """Удалить объект"""
        try:
            obj = self.get_by_id(obj_id)
            if obj:
                obj.delete()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    def search(self, **filters) -> List[BaseModel]:
        """Поиск объектов по фильтрам"""
        query = self.model_class.query
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                if isinstance(value, str):
                    # Для строковых полей используем LIKE
                    column = getattr(self.model_class, key)
                    query = query.filter(column.ilike(f'%{value}%'))
                else:
                    query = query.filter(getattr(self.model_class, key) == value)
        return query.all()
    
    def get_paginated(self, page: int = 1, per_page: int = 20, **filters):
        """Получить объекты с пагинацией"""
        query = self.model_class.query
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                if isinstance(value, str):
                    column = getattr(self.model_class, key)
                    query = query.filter(column.ilike(f'%{value}%'))
                else:
                    query = query.filter(getattr(self.model_class, key) == value)
        
        return query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
    def exists(self, **filters) -> bool:
        """Проверить существование объекта"""
        query = self.model_class.query
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        return query.first() is not None
    
    def count(self, **filters) -> int:
        """Получить количество объектов"""
        query = self.model_class.query
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                if isinstance(value, str):
                    column = getattr(self.model_class, key)
                    query = query.filter(column.ilike(f'%{value}%'))
                else:
                    query = query.filter(getattr(self.model_class, key) == value)
        return query.count()













