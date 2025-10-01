from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Role, Group, Student, Direction, Cafedral
from extensions import db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Неверное имя пользователя или пароль. Попробуйте снова.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        return redirect(url_for('main.index'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role_name = request.form.get('role')
        group_name = request.form.get('group')
        
        # Check if user already exists
        user = User.query.filter_by(username=username).first()
        
        if user:
            flash('Пользователь с таким именем уже существует', 'danger')
            return redirect(url_for('auth.register'))
        
        # Get selected role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            # Create roles if they don't exist
            student_role = Role(name='студент')
            teacher_role = Role(name='преподаватель')
            db.session.add(student_role)
            db.session.add(teacher_role)
            db.session.commit()
            
            # Get the role again
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
        
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 