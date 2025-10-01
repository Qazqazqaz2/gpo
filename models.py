from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    
    # Relationships
    role_navigation = db.relationship("Role", back_populates="users")
    resposeble_ask_forms = db.relationship("AskForm", foreign_keys="AskForm.ask_form_resposeble", overlaps="ask_form_resposeble_navigation")
    consultant_leader_ask_forms = db.relationship("AskForm", foreign_keys="AskForm.consultant_leader", overlaps="consultant_leader_navigation")
    practice_leader_ask_forms = db.relationship("AskForm", foreign_keys="AskForm.practice_leader", overlaps="practice_leader_navigation")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def roles(self):
        # Return a list of roles (in this case, just one)
        try:
            if self.role_navigation:
                return [self.role_navigation.name]
        except:
            pass
        return []

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    users = db.relationship("User", back_populates="role_navigation")

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    patronymic = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # Relationships
    group_navigation = db.relationship("Group")
    student_ask_forms = db.relationship("AskForm", foreign_keys="AskForm.student", overlaps="student_navigation")

class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    direction_id = db.Column(db.Integer, db.ForeignKey('directions.id'), nullable=True)
    
    # Relationships
    direction_navigation = db.relationship("Direction", back_populates="groups")
    ask_forms = db.relationship("AskForm", back_populates="group_navigation")

class Direction(db.Model):
    __tablename__ = 'directions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cafedral_id = db.Column(db.Integer, db.ForeignKey('cafedrals.id'), nullable=True)
    
    # Relationships
    cafedral_navigation = db.relationship("Cafedral", back_populates="directions")
    groups = db.relationship("Group", back_populates="direction_navigation")
    practic_times = db.relationship("PracticTime", back_populates="direction_navigation")

class Cafedral(db.Model):
    __tablename__ = 'cafedrals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    directions = db.relationship("Direction", back_populates="cafedral_navigation")

class PracticeType(db.Model):
    __tablename__ = 'practice_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    ask_forms = db.relationship("AskForm", back_populates="practice_type_navigation")

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    
    # Relationships
    contracts = db.relationship("Contract", back_populates="organization_navigation")

class Contract(db.Model):
    __tablename__ = 'contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_number = db.Column(db.String(100), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    date_start = db.Column(db.DateTime, nullable=True)
    date_end = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    organization_navigation = db.relationship("Organization", back_populates="contracts")
    ask_forms = db.relationship("AskForm", back_populates="contract_navigation")

class Status(db.Model):
    __tablename__ = 'statuses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    # Relationships
    ask_forms = db.relationship("AskForm", back_populates="status_navigation")

class PracticTime(db.Model):
    __tablename__ = 'practic_times'
    
    id = db.Column(db.Integer, primary_key=True)
    date_start = db.Column(db.DateTime, nullable=True)
    date_end = db.Column(db.DateTime, nullable=True)
    direction_id = db.Column(db.Integer, db.ForeignKey('directions.id'), nullable=False)
    
    # Relationships
    direction_navigation = db.relationship("Direction", back_populates="practic_times")

class AskForm(db.Model):
    __tablename__ = 'ask_forms'
    
    id = db.Column(db.Integer, primary_key=True)
    practice_type = db.Column(db.Integer, db.ForeignKey('practice_types.id'), nullable=False)
    group = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    contract = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    ask_form_resposeble = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    consultant_leader = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    practice_leader = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    student = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    # Relationships
    practice_type_navigation = db.relationship("PracticeType", back_populates="ask_forms")
    group_navigation = db.relationship("Group", back_populates="ask_forms")
    contract_navigation = db.relationship("Contract", back_populates="ask_forms")
    ask_form_resposeble_navigation = db.relationship("User", foreign_keys=[ask_form_resposeble], overlaps="resposeble_ask_forms")
    consultant_leader_navigation = db.relationship("User", foreign_keys=[consultant_leader], overlaps="consultant_leader_ask_forms")
    practice_leader_navigation = db.relationship("User", foreign_keys=[practice_leader], overlaps="practice_leader_ask_forms")
    status_navigation = db.relationship("Status", back_populates="ask_forms")
    student_navigation = db.relationship("Student", foreign_keys=[student], overlaps="student_ask_forms")

class Field(db.Model):
    __tablename__ = 'fields'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(35), nullable=False)
    block = db.Column(db.String(255), nullable=True)
    page = db.Column(db.String(255), nullable=True)
    text = db.Column(db.Text, nullable=True)
    mutability = db.Column(db.String(255), nullable=True)

class Template(db.Model):
    __tablename__ = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    template_body = db.Column(db.Text, nullable=False) 