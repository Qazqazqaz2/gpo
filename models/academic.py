"""
Модели академической структуры
"""
from .base import BaseModel
from extensions import db


class Cafedral(BaseModel):
    """Модель кафедры"""
    __tablename__ = 'cafedrals'
    
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    directions = db.relationship("Direction", back_populates="cafedral", cascade="all, delete-orphan")
    
    @classmethod
    def get_by_name(cls, name):
        """Получить кафедру по имени"""
        return cls.query.filter_by(name=name).first()
    
    def __repr__(self):
        return f'<Cafedral {self.name}>'


class Direction(BaseModel):
    """Модель направления подготовки"""
    __tablename__ = 'directions'
    
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(20), unique=True, nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    cafedral_id = db.Column(db.Integer, db.ForeignKey('cafedrals.id'), nullable=True)
    
    # Relationships
    cafedral = db.relationship("Cafedral", back_populates="directions")
    groups = db.relationship("Group", back_populates="direction", cascade="all, delete-orphan")
    practice_times = db.relationship("PracticTime", back_populates="direction", cascade="all, delete-orphan")
    
    @classmethod
    def get_by_name(cls, name):
        """Получить направление по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_by_code(cls, code):
        """Получить направление по коду"""
        return cls.query.filter_by(code=code).first()
    
    def __repr__(self):
        return f'<Direction {self.name}>'


class Group(BaseModel):
    """Модель группы"""
    __tablename__ = 'groups'
    
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    year = db.Column(db.Integer, nullable=True)
    direction_id = db.Column(db.Integer, db.ForeignKey('directions.id'), nullable=True)
    
    # Relationships
    direction = db.relationship("Direction", back_populates="groups")
    students = db.relationship("Student", back_populates="group", cascade="all, delete-orphan")
    ask_forms = db.relationship("AskForm", back_populates="group")
    consultant_assignments = db.relationship(
        "ConsultantGroup",
        back_populates="group",
        cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_by_name(cls, name):
        """Получить группу по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_by_direction(cls, direction_id):
        """Получить группы по направлению"""
        return cls.query.filter_by(direction_id=direction_id).all()
    
    def get_students_count(self):
        """Получить количество студентов в группе"""
        return len(self.students)
    
    def __repr__(self):
        return f'<Group {self.name}>'


class Student(BaseModel):
    """Модель студента"""
    __tablename__ = 'students'
    
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    patronymic = db.Column(db.String(100), nullable=True)
    student_id = db.Column(db.String(20), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # Relationships
    group = db.relationship("Group", back_populates="students")
    ask_forms = db.relationship("AskForm", back_populates="student")
    
    @property
    def full_name(self):
        """Получить полное имя студента"""
        parts = [self.surname, self.name]
        if self.patronymic:
            parts.append(self.patronymic)
        return ' '.join(parts)
    
    @classmethod
    def get_by_student_id(cls, student_id):
        """Получить студента по номеру студенческого билета"""
        return cls.query.filter_by(student_id=student_id).first()
    
    @classmethod
    def get_by_group(cls, group_id):
        """Получить студентов группы"""
        return cls.query.filter_by(group_id=group_id).all()
    
    @classmethod
    def search_by_name(cls, name):
        """Поиск студентов по имени"""
        return cls.query.filter(
            cls.name.ilike(f'%{name}%') | 
            cls.surname.ilike(f'%{name}%') |
            cls.patronymic.ilike(f'%{name}%')
        ).all()
    
    def __repr__(self):
        return f'<Student {self.full_name}>'


class ConsultantGroup(BaseModel):
    """Закрепление группы за преподавателем-консультантом"""
    __tablename__ = 'consultant_groups'
    
    consultant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False, unique=True)
    
    consultant = db.relationship("User", back_populates="consultant_groups")
    group = db.relationship("Group", back_populates="consultant_assignments")


class PracticTime(BaseModel):
    """Модель времени практики"""
    __tablename__ = 'practic_times'
    
    name = db.Column(db.String(100), nullable=False)
    date_start = db.Column(db.DateTime, nullable=True)
    date_end = db.Column(db.DateTime, nullable=True)
    direction_id = db.Column(db.Integer, db.ForeignKey('directions.id'), nullable=False)
    
    # Relationships
    direction = db.relationship("Direction", back_populates="practice_times")
    
    @classmethod
    def get_current_practice(cls, direction_id=None):
        """Получить текущую практику"""
        from datetime import datetime
        now = datetime.utcnow()
        
        query = cls.query.filter(
            cls.date_start <= now,
            cls.date_end >= now
        )
        
        if direction_id:
            query = query.filter_by(direction_id=direction_id)
        
        return query.first()
    
    @classmethod
    def get_upcoming_practice(cls, direction_id=None):
        """Получить предстоящую практику"""
        from datetime import datetime
        now = datetime.utcnow()
        
        query = cls.query.filter(cls.date_start > now)
        
        if direction_id:
            query = query.filter_by(direction_id=direction_id)
        
        return query.order_by(cls.date_start).first()
    
    def __repr__(self):
        return f'<PracticTime {self.name}>'
