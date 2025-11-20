"""
Модели организаций и договоров
"""
from datetime import datetime
from .base import BaseModel
from extensions import db


class Organization(BaseModel):
    """Модель организации"""
    __tablename__ = 'organizations'
    
    name = db.Column(db.String(200), nullable=False, index=True)
    address = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    contracts = db.relationship("Contract", back_populates="organization", cascade="all, delete-orphan")
    
    @classmethod
    def get_by_name(cls, name):
        """Получить организацию по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def search_by_name(cls, name):
        """Поиск организаций по имени"""
        return cls.query.filter(cls.name.ilike(f'%{name}%')).all()
    
    @classmethod
    def get_active(cls):
        """Получить активные организации"""
        return cls.query.filter_by(is_active=True).all()
    
    def get_active_contracts(self):
        """Получить активные договоры организации"""
        return [contract for contract in self.contracts if contract.is_active]
    
    def __repr__(self):
        return f'<Organization {self.name}>'


class Contract(BaseModel):
    """Модель договора"""
    __tablename__ = 'contracts'
    
    contract_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    date_start = db.Column(db.DateTime, nullable=True)
    date_end = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    max_students = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", back_populates="contracts")
    ask_forms = db.relationship("AskForm", back_populates="contract")
    
    @property
    def is_expired(self):
        """Проверить, истек ли договор"""
        if not self.date_end:
            return False
        return datetime.utcnow() > self.date_end
    
    @property
    def is_current(self):
        """Проверить, действует ли договор в настоящее время"""
        if not self.date_start or not self.date_end:
            return self.is_active
        now = datetime.utcnow()
        return self.date_start <= now <= self.date_end and self.is_active
    
    @property
    def days_until_expiry(self):
        """Получить количество дней до истечения договора"""
        if not self.date_end:
            return None
        delta = self.date_end - datetime.utcnow()
        return delta.days if delta.days > 0 else 0
    
    @classmethod
    def get_by_number(cls, contract_number):
        """Получить договор по номеру"""
        return cls.query.filter_by(contract_number=contract_number).first()
    
    @classmethod
    def get_active(cls):
        """Получить активные договоры"""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_current(cls):
        """Получить действующие договоры"""
        now = datetime.utcnow()
        return cls.query.filter(
            cls.is_active == True,
            cls.date_start <= now,
            cls.date_end >= now
        ).all()
    
    @classmethod
    def get_expiring_soon(cls, days=30):
        """Получить договоры, истекающие в ближайшие дни"""
        from datetime import timedelta
        future_date = datetime.utcnow() + timedelta(days=days)
        return cls.query.filter(
            cls.is_active == True,
            cls.date_end <= future_date,
            cls.date_end >= datetime.utcnow()
        ).all()
    
    def get_used_slots(self):
        """Получить количество использованных слотов"""
        return len([form for form in self.ask_forms if form.is_approved])
    
    def get_available_slots(self):
        """Получить количество доступных слотов"""
        if not self.max_students:
            return None
        return max(0, self.max_students - self.get_used_slots())
    
    def has_available_slots(self):
        """Проверить, есть ли доступные слоты"""
        if not self.max_students:
            return True
        return self.get_available_slots() > 0
    
    def __repr__(self):
        return f'<Contract {self.contract_number}>'
