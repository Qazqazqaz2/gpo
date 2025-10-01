from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_file
from flask_login import login_required, current_user
from models import User, Role, Student, Group, PracticeType, Contract, Organization, AskForm, Status
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfWriter, PdfReader
import tempfile
from test_pdf import replace_text, replace_underline, process_template
from docx import Document
import re
from datetime import datetime
from flask import session

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        # Redirect to respective dashboard based on user role
        if 'преподаватель' in current_user.roles:
            return redirect(url_for('main.teacher_dashboard'))
        else:
            return redirect(url_for('main.student_dashboard'))
    
    return render_template('login.html')

@main.route('/profile')
@login_required
def profile():
    student_info = None
    if 'студент' in current_user.roles:
        # Get student record for current user
        student = Student.query.filter_by(name=current_user.username).first()
        if student and student.group_navigation:
            student_info = {
                'group': student.group_navigation.name,
                'surname': student.surname,
                'name': student.name,
                'patronymic': student.patronymic
            }
    
    return render_template('profile.html', user=current_user, student_info=student_info)

@main.route('/student/dashboard')
@login_required
def student_dashboard():
    # Check if user is a student
    if 'студент' not in current_user.roles:
        flash('У вас нет доступа к этой странице', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all forms for the current student
    ask_forms = []
    student = Student.query.filter_by(name=current_user.username).first()
    
    if student:
        ask_forms = AskForm.query.filter_by(student=student.id).all()
    
    return render_template('student_dashboard.html', ask_forms=ask_forms)

@main.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    # Check if user is a teacher
    if 'преподаватель' not in current_user.roles:
        flash('У вас нет доступа к этой странице', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all groups for the dropdown
    groups = Group.query.order_by(Group.name).all()
    
    return render_template('teacher_dashboard.html', groups=groups)

@main.route('/teacher/students/<int:group_id>')
@login_required
def students_by_group(group_id):
    # Check if user is a teacher
    if 'преподаватель' not in current_user.roles:
        flash('У вас нет доступа к этой странице', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all students in the group
    students = Student.query.filter_by(group_id=group_id).all()
    group = Group.query.get_or_404(group_id)
    
    return render_template('student_list.html', students=students, group=group)

@main.route('/practice-form', methods=['GET', 'POST'])
@login_required
def practice_form():
    # Check if user is a student
    if 'студент' not in current_user.roles:
        flash('У вас нет доступа к этой странице', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Get form data
        practice_type = request.form.get('practice_type')
        group = request.form.get('group')
        student = request.form.get('student')
        consultant_leader = request.form.get('consultant_leader')
        practice_leader = request.form.get('practice_leader')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        
        # Check if using custom organization
        use_custom_org = 'use_custom_org' in request.form
        
        # Store user data in session for PDF generation
        session['phone_number'] = phone_number
        session['email'] = email
        
        # Handle contract selection or custom organization
        if use_custom_org:
            # Get custom organization data
            custom_org_name = request.form.get('custom_org_name')
            custom_org_address = request.form.get('custom_org_address')
            custom_contract_num = request.form.get('custom_contract_num')
            
            # Create a new organization record
            new_org = Organization(
                name=custom_org_name,
                address=custom_org_address
            )
            db.session.add(new_org)
            db.session.flush()  # Get ID without committing
            
            # Create a new contract record
            today = datetime.now()
            new_contract = Contract(
                contract_number=custom_contract_num or f"Временный №{today.strftime('%Y%m%d%H%M%S')}",
                organization_id=new_org.id,
                date_start=today,
                date_end=today.replace(year=today.year + 1)  # One year contract
            )
            db.session.add(new_contract)
            db.session.flush()  # Get ID without committing
            
            # Use the new contract
            contract = new_contract.id
            
            # Save custom organization info in session for PDF generation
            session['custom_organization'] = True
            session['organization_name'] = custom_org_name
            session['organization_address'] = custom_org_address
        else:
            # Using existing contract
            contract = request.form.get('contract')
            session['custom_organization'] = False
        
        # Create new form with status 0 (pending)
        status = Status.query.filter_by(name='0').first()
        if not status:
            status = Status(name='0')
            db.session.add(status)
            db.session.commit()
        
        # Create the form
        ask_form = AskForm(
            practice_type=practice_type,
            group=group,
            contract=contract,
            ask_form_resposeble=current_user.id,  # Current student is responsible
            consultant_leader=consultant_leader,
            practice_leader=practice_leader,
            status=status.id,
            student=student
        )
        
        db.session.add(ask_form)
        db.session.commit()
        
        flash('Заявка на практику успешно отправлена!', 'success')
        
        # Generate PDF
        pdf = generate_practice_pdf(ask_form)
        
        # Return PDF file
        return send_file(
            BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='practice_application.pdf'
        )
    
    # Get current student data based on username
    current_student = Student.query.filter_by(name=current_user.username).first()
    
    # Get default group (722-1)
    default_group = Group.query.filter_by(name='722-1').first()
    if not default_group:
        # Don't create here, it should be created in create_defaults.py
        flash('Группа 722-1 не найдена в базе данных', 'warning')
        default_group = Group.query.first()  # Get any group as fallback
    
    # Get data for form dropdowns
    practice_types = PracticeType.query.all()
    groups = Group.query.all()
    contracts = Contract.query.join(Organization, Contract.organization_id == Organization.id).all()
    students = Student.query.all()
    teachers = User.query.join(Role, User.role_id == Role.id).filter(Role.name == 'преподаватель').all()
    
    return render_template('practice_form.html', 
                          practice_types=practice_types,
                          groups=groups,
                          contracts=contracts,
                          students=students,
                          teachers=teachers,
                          current_student=current_student,
                          default_group=default_group)

@main.route('/view-form/<int:form_id>')
@login_required
def view_form(form_id):
    ask_form = AskForm.query.get_or_404(form_id)
    
    # Check permissions
    if 'преподаватель' not in current_user.roles and current_user.id != ask_form.ask_form_resposeble:
        flash('У вас нет доступа к этой форме', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('view_form.html', ask_form=ask_form)

@main.route('/update-form-status/<int:form_id>/<int:status>')
@login_required
def update_form_status(form_id, status):
    # Check if user is a teacher
    if 'преподаватель' not in current_user.roles:
        flash('У вас нет доступа к этой функции', 'danger')
        return redirect(url_for('main.index'))
    
    ask_form = AskForm.query.get_or_404(form_id)
    status_obj = Status.query.filter_by(name=str(status)).first()
    
    if not status_obj:
        status_obj = Status(name=str(status))
        db.session.add(status_obj)
        db.session.commit()
    
    ask_form.status = status_obj.id
    db.session.commit()
    
    if status == 0:
        flash('Форма отклонена. Студент должен заполнить её заново.', 'warning')
    elif status == 2:
        flash('Форма принята!', 'success')
    
    return redirect(url_for('main.view_form', form_id=form_id))

def generate_practice_pdf(ask_form):
    # Path to template DOCX
    template_path = os.path.join(current_app.root_path, 'ShABLON_732_grupp_Zayavlenie_na_prokhozhdenie_praktiki-1.docx')
    
    # Get related data
    student = Student.query.get(ask_form.student)
    group = Group.query.get(ask_form.group)
    practice_type = PracticeType.query.get(ask_form.practice_type)
    
    # Check if using custom organization
    use_custom_org = session.get('custom_organization', False)
    
    if use_custom_org:
        # Use the custom organization data from session
        organization_name = session.get('organization_name', '')
        organization_address = session.get('organization_address', '')
    else:
        # Use organization from the selected contract
        contract = Contract.query.get(ask_form.contract)
        organization = Organization.query.get(contract.organization_id)
        organization_name = organization.name
        organization_address = organization.address
    
    consultant = User.query.get(ask_form.consultant_leader)
    practice_leader = User.query.get(ask_form.practice_leader)
    
    # Get phone number and email from session
    phone_number = session.get('phone_number', '+7XXXXXXXXXX')
    email = session.get('email', 'student@example.com')
    
    # Prepare data for template filling
    full_student_name = f"{student.surname} {student.name} {student.patronymic}"
    today_date = datetime.now().strftime('%d.%m.%Y')
    
    # Data for filling the docx template
    data = {
        'ГРУППА0': group.name,
        'ФИОСТУДЕНТА': full_student_name,
        'НОМЕРСТУДЕНТА': phone_number,
        'МАИЛ': email,
        'ОРГАНИЗАЦИЯ': organization_name,
        'АДРЕС': organization_address,
        'РУКОВОДИТЕЛЬ': practice_leader.username,
        'ДАТА': today_date
    }
    
    try:
        # Process the template and generate PDF
        pdf_data = process_template(template_path, data)
        
        # If a string is returned (file path), read the file
        if isinstance(pdf_data, str):
            with open(pdf_data, 'rb') as f:
                return f.read()
        
        # Otherwise, the binary data was returned directly
        return pdf_data
        
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        raise Exception(f"Ошибка при генерации PDF: {str(e)}") 