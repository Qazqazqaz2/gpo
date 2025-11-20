"""
Модели практики и заявок
"""
from .base import BaseModel
from extensions import db


class PracticeType(BaseModel):
    """Модель типа практики"""
    __tablename__ = 'practice_types'
    
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    duration_days = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    ask_forms = db.relationship("AskForm", back_populates="practice_type")
    
    @classmethod
    def get_by_name(cls, name):
        """Получить тип практики по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_active(cls):
        """Получить активные типы практики"""
        return cls.query.filter_by(is_active=True).all()
    
    def __repr__(self):
        return f'<PracticeType {self.name}>'


class Status(BaseModel):
    """Модель статуса заявки"""
    __tablename__ = 'statuses'
    
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    color = db.Column(db.String(7), nullable=True)  # HEX цвет
    is_final = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    ask_forms = db.relationship("AskForm", back_populates="status")
    
    @classmethod
    def get_by_name(cls, name):
        """Получить статус по имени"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def create_default_statuses(cls):
        """Создать статусы по умолчанию"""
        default_statuses = [
            {'name': '0', 'description': 'На рассмотрении', 'color': '#ffc107', 'is_final': False},
            {'name': '1', 'description': 'В процессе', 'color': '#17a2b8', 'is_final': False},
            {'name': '2', 'description': 'Одобрено', 'color': '#28a745', 'is_final': True},
            {'name': '3', 'description': 'Отклонено', 'color': '#dc3545', 'is_final': True}
        ]
        
        for status_data in default_statuses:
            existing_status = cls.get_by_name(status_data['name'])
            if not existing_status:
                status = cls(**status_data)
                status.save()
    
    def __repr__(self):
        return f'<Status {self.name}>'


class AskForm(BaseModel):
    """Модель заявки на практику"""
    __tablename__ = 'ask_forms'
    
    # Основные поля
    practice_type_id = db.Column(db.Integer, db.ForeignKey('practice_types.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    # Ответственные лица
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    consultant_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    practice_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Статус
    status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    
    # Дополнительные поля
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    consultant_contract_signature = db.Column(db.String(255), nullable=True)
    consultant_contract_signed_at = db.Column(db.DateTime, nullable=True)
    consultant_application_signature = db.Column(db.String(255), nullable=True)
    consultant_application_signed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    practice_type = db.relationship("PracticeType", back_populates="ask_forms")
    group = db.relationship("Group", back_populates="ask_forms")
    contract = db.relationship("Contract", back_populates="ask_forms")
    student = db.relationship("Student", back_populates="ask_forms")
    status = db.relationship("Status", back_populates="ask_forms")
    
    # Пользователи
    responsible_user = db.relationship("User", foreign_keys=[responsible_user_id], back_populates="responsible_forms")
    consultant_user = db.relationship("User", foreign_keys=[consultant_leader_id], back_populates="consultant_forms")
    practice_leader_user = db.relationship("User", foreign_keys=[practice_leader_id], back_populates="practice_leader_forms")
    diary = db.relationship("PracticeDiary", back_populates="ask_form", uselist=False, cascade="all, delete-orphan")
    
    @property
    def is_pending(self):
        """Проверить, находится ли заявка на рассмотрении"""
        return self.status.name == '0'
    
    @property
    def is_approved(self):
        """Проверить, одобрена ли заявка"""
        return self.status.name == '2'
    
    @property
    def is_rejected(self):
        """Проверить, отклонена ли заявка"""
        return self.status.name == '3'
    
    @property
    def is_in_progress(self):
        """Проверить, находится ли заявка в процессе"""
        return self.status.name == '1'
    
    @classmethod
    def get_by_student(cls, student_id):
        """Получить заявки студента"""
        return cls.query.filter_by(student_id=student_id).all()
    
    @classmethod
    def get_by_status(cls, status_name):
        """Получить заявки по статусу"""
        return cls.query.join(Status).filter(Status.name == status_name).all()
    
    @classmethod
    def get_by_group(cls, group_id):
        """Получить заявки группы"""
        return cls.query.filter_by(group_id=group_id).all()
    
    @classmethod
    def get_pending(cls):
        """Получить заявки на рассмотрении"""
        return cls.get_by_status('0')
    
    @classmethod
    def get_approved(cls):
        """Получить одобренные заявки"""
        return cls.get_by_status('2')
    
    def approve(self):
        """Одобрить заявку"""
        approved_status = Status.get_by_name('2')
        if approved_status:
            self.status_id = approved_status.id
            self.save()
    
    def reject(self):
        """Отклонить заявку"""
        rejected_status = Status.get_by_name('3')
        if rejected_status:
            self.status_id = rejected_status.id
            self.save()
    
    def set_in_progress(self):
        """Установить статус "В процессе" """
        in_progress_status = Status.get_by_name('1')
        if in_progress_status:
            self.status_id = in_progress_status.id
            self.save()
    
    def __repr__(self):
        return f'<AskForm {self.id} - {self.student.full_name if self.student else "Unknown"}>'


class PracticeDiary(BaseModel):
    """Дневник практики"""
    __tablename__ = 'practice_diaries'
    
    ask_form_id = db.Column(db.Integer, db.ForeignKey('ask_forms.id'), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    faculty = db.Column(db.String(255), nullable=True)
    course = db.Column(db.String(50), nullable=True)
    group_name = db.Column(db.String(100), nullable=True)
    practice_place = db.Column(db.String(255), nullable=True)
    practice_period = db.Column(db.String(255), nullable=True)
    work_plan = db.Column(db.Text, nullable=True)
    
    assignment_theme = db.Column(db.Text, nullable=True)
    assignment_goal = db.Column(db.Text, nullable=True)
    assignment_tasks = db.Column(db.Text, nullable=True)
    
    daily_entries = db.Column(db.Text, nullable=True)
    instruction_notes = db.Column(db.Text, nullable=True)
    
    evaluation_note = db.Column(db.Text, nullable=True)
    evaluation_rewards = db.Column(db.Text, nullable=True)
    evaluation_grade = db.Column(db.String(50), nullable=True)
    
    university_conclusion = db.Column(db.Text, nullable=True)
    university_grade = db.Column(db.String(50), nullable=True)
    
    student_signature = db.Column(db.String(255), nullable=True)
    student_signed_at = db.Column(db.DateTime, nullable=True)
    consultant_signature = db.Column(db.String(255), nullable=True)
    consultant_signed_at = db.Column(db.DateTime, nullable=True)
    practice_leader_signature = db.Column(db.String(255), nullable=True)
    practice_leader_signed_at = db.Column(db.DateTime, nullable=True)
    
    ask_form = db.relationship("AskForm", back_populates="diary")
    student = db.relationship("Student")
