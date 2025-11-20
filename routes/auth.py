from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Role, Group, Student, Direction, Cafedral
from services import UserService, StudentService
from utils.decorators import handle_errors
from utils.exceptions import ValidationError, BusinessLogicError
from extensions import db
import logging

auth = Blueprint('auth', __name__)

def _resolve_student_username(raw_username: str):
    """
    Позволяет студентам входить по привычному ФИО.
    Если пользователь ввёл ФИО вместо технического логина (фамилия_имя_группа),
    пытаемся найти запись студента и вычислить фактический username.
    """
    if not raw_username:
        return None
    
    normalized = ' '.join(raw_username.strip().split())
    fio_parts = normalized.split(' ')
    if len(fio_parts) < 2:
        return None
    
    surname, name, *rest = fio_parts
    query = Student.query.filter(
        Student.surname.ilike(surname),
        Student.name.ilike(name)
    )
    if rest:
        patronymic = rest[0]
        query = query.filter(Student.patronymic.ilike(patronymic))
    
    student = query.first()
    if not student or not student.group:
        return None
    
    group_suffix = student.group.name.replace('-', '').replace(' ', '').lower()
    suggestions = [
        f"{student.surname.lower()}_{student.name.lower()}_{group_suffix}",
        f"{student.surname.lower()}_{student.name.lower()}"
    ]
    
    for candidate in suggestions:
        user = User.query.filter_by(username=candidate).first()
        if user:
            return user
    return None


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username_input).first()
        if not user:
            user = _resolve_student_username(username_input)
        
        if user:
            print(f'[LOGIN] Найден user: {user.username} (is_active={user.is_active})')
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            print('[LOGIN] Успех!')
            return redirect(url_for('main.index'))
        
        print('[LOGIN] Неудача (либо не найден, либо не активен, либо пароль не тот)')
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role_name = request.form.get('role')
        group_name = request.form.get('group')
        
        current_app.logger.info(f"REGISTER ATTEMPT: username='{username}', role='{role_name}', group='{group_name}'")
        current_app.logger.info(f"REGISTER ATTEMPT: IP={request.remote_addr}, User-Agent={request.headers.get('User-Agent', 'Unknown')}")
        
        if not username or not password:
            current_app.logger.warning(f"REGISTER FAILED: Empty credentials - username='{username}', password provided={bool(password)}")
            flash('Пожалуйста, введите имя пользователя и пароль.', 'warning')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        user = User.query.filter_by(username=username).first()
        
        if user:
            current_app.logger.warning(f"REGISTER FAILED: User '{username}' already exists (ID: {user.id})")
            flash('Пользователь с таким именем уже существует', 'danger')
            return redirect(url_for('auth.register'))
        
        # Get selected role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            # Create roles if they don't exist
            required_roles = ['студент', 'преподаватель', 'преподаватель консультант']
            for required_role_name in required_roles:
                if not Role.query.filter_by(name=required_role_name).first():
                    db.session.add(Role(name=required_role_name))
            db.session.commit()
            role = Role.query.filter_by(name=role_name).first()
        
        # Create new user
        new_user = User(username=username, role_id=role.id)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # If the user is a student and provided a group
        if role_name == 'студент' and group_name:
            # Check if group exists
            group = Group.query.filter_by(name=group_name).first()
            
            # If group doesn't exist, create it
            if not group:
                # Need to find or create direction first
                default_direction = Direction.query.first()
                
                if not default_direction:
                    # Create a default cafedral if none exists
                    default_cafedral = Cafedral.query.first()
                    if not default_cafedral:
                        default_cafedral = Cafedral(name="ФСУ")
                        db.session.add(default_cafedral)
                        db.session.commit()
                    
                    # Create default direction
                    default_direction = Direction(
                        name="Программная инженерия", 
                        cafedral_id=default_cafedral.id
                    )
                    db.session.add(default_direction)
                    db.session.commit()
                
                # Create the new group
                group = Group(name=group_name, direction_id=default_direction.id)
                db.session.add(group)
                db.session.commit()
                
                flash(f'Группа {group_name} создана', 'success')
            
            # Create student record
            student = Student(
                name=username,
                surname=username,
                patronymic="",
                group_id=group.id
            )
            db.session.add(student)
            db.session.commit()
        
        try:
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            current_app.logger.info(f"REGISTER SUCCESS: User '{username}' registered successfully with role '{role_name}'")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"REGISTER ERROR: Exception during registration for username='{username}': {str(e)}")
            flash('Произошла ошибка при регистрации. Попробуйте снова.', 'danger')
            return redirect(url_for('auth.register'))
    
    current_app.logger.info("REGISTER PAGE: Register page accessed")
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 