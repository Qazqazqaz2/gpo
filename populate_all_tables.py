from app import app
from extensions import db
from models import User, Role, Student, Group, PracticeType, Contract, Organization, Direction, Cafedral, Status, AskForm
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

with app.app_context():
    print("Начало заполнения базы данных...")
    
    # 1. Создание ролей
    roles = {
        'студент': Role.query.filter_by(name='студент').first(),
        'преподаватель': Role.query.filter_by(name='преподаватель').first()
    }
    
    for role_name, role in roles.items():
        if not role:
            role = Role(name=role_name)
            db.session.add(role)
            print(f"Добавлена роль: {role_name}")
    
    db.session.commit()
    
    # 2. Создание кафедр и направлений
    cafedral_names = ["ФСУ", "АОИ", "ИСР", "ИСЭ", "КИБЭВС"]
    cafedrals = {}
    
    for name in cafedral_names:
        cafedral = Cafedral.query.filter_by(name=name).first()
        if not cafedral:
            cafedral = Cafedral(name=name)
            db.session.add(cafedral)
            print(f"Добавлена кафедра: {name}")
        cafedrals[name] = cafedral
    
    db.session.commit()
    
    # 3. Добавление направлений
    direction_names = {
        "Программная инженерия": "ФСУ",
        "Информационные системы": "АОИ",
        "Управление в технических системах": "ИСЭ",
        "Информационная безопасность": "КИБЭВС",
        "Социальная работа": "ИСР"
    }
    
    directions = {}
    for name, cafedral_name in direction_names.items():
        direction = Direction.query.filter_by(name=name).first()
        if not direction:
            direction = Direction(
                name=name, 
                cafedral_id=cafedrals[cafedral_name].id
            )
            db.session.add(direction)
            print(f"Добавлено направление: {name}")
        directions[name] = direction
    
    db.session.commit()
    
    # 4. Добавление групп
    group_names = ["722-1", "732-1", "742-1", "761-1", "711М"]
    groups = {}
    
    for name in group_names:
        group = Group.query.filter_by(name=name).first()
        if not group:
            # Случайное направление
            direction = random.choice(list(directions.values()))
            group = Group(name=name, direction_id=direction.id)
            db.session.add(group)
            print(f"Добавлена группа: {name} (направление: {direction.name})")
        groups[name] = group
    
    db.session.commit()
    
    # 5. Добавление организаций
    org_names = [
        {"name": "ТУСУР", "address": "г. Томск, пр. Ленина, 40"},
        {"name": "Микран", "address": "г. Томск, пр. Кирова, 51д"},
        {"name": "Элеси", "address": "г. Томск, ул. Алтайская, 161А"},
        {"name": "ТомскАСУпроект", "address": "г. Томск, ул. Пушкина, 63"}
    ]
    
    organizations = {}
    for org_data in org_names:
        org = Organization.query.filter_by(name=org_data["name"]).first()
        if not org:
            org = Organization(name=org_data["name"], address=org_data["address"])
            db.session.add(org)
            print(f"Добавлена организация: {org_data['name']}")
        organizations[org_data["name"]] = org
    
    db.session.commit()
    
    # 6. Создание пользователей и студентов
    users_data = [
        {"username": "Артемка", "password": "password", "role": "студент", "group": "722-1"},
        {"username": "Иванов И.И.", "password": "password", "role": "студент", "group": "732-1"},
        {"username": "Петров П.П.", "password": "password", "role": "студент", "group": "742-1"},
        {"username": "Сидоров С.С.", "password": "password", "role": "преподаватель"},
        {"username": "Руководитель П. П.", "password": "password", "role": "преподаватель"},
        {"username": "Руководитель Р. Р.", "password": "password", "role": "преподаватель"}
    ]
    
    users = {}
    for user_data in users_data:
        user = User.query.filter_by(username=user_data["username"]).first()
        if not user:
            role = Role.query.filter_by(name=user_data["role"]).first()
            user = User(username=user_data["username"], role_id=role.id)
            user.set_password(user_data["password"])
            db.session.add(user)
            print(f"Добавлен пользователь: {user_data['username']} (роль: {user_data['role']})")
            
            # Если студент, создаем запись студента
            if user_data["role"] == "студент":
                group = Group.query.filter_by(name=user_data["group"]).first()
                
                # Разбиваем имя на фамилию и имя
                parts = user_data["username"].split()
                surname = parts[0] if len(parts) > 0 else user_data["username"]
                name = parts[1] if len(parts) > 1 else ""
                patronymic = parts[2] if len(parts) > 2 else ""
                
                student = Student.query.filter_by(name=name or user_data["username"]).first()
                if not student:
                    student = Student(
                        name=name or user_data["username"],
                        surname=surname,
                        patronymic=patronymic,
                        group_id=group.id
                    )
                    db.session.add(student)
                    print(f"Добавлен студент: {surname} {name} {patronymic} (группа: {user_data['group']})")
        
        users[user_data["username"]] = user
    
    db.session.commit()
    
    # 7. Типы практик
    practice_types_names = ["Учебная", "Преддипломная", "Производственная"]
    practice_types = {}
    
    for name in practice_types_names:
        pt = PracticeType.query.filter_by(name=name).first()
        if not pt:
            pt = PracticeType(name=name)
            db.session.add(pt)
            print(f"Добавлен тип практики: {name}")
        practice_types[name] = pt
    
    db.session.commit()
    
    # 8. Создание договоров
    contract_numbers = [
        "1232321",
        "ДОГ-2025-001",
        "ПРК-2025-002",
        "СТЖ-2025-003",
        "ДП-2025-123",
        "Заявление",
        "Договор"
    ]
    
    contracts = {}
    for contract_number in contract_numbers:
        contract = Contract.query.filter_by(contract_number=contract_number).first()
        if not contract:
            org = random.choice(list(organizations.values()))
            date_start = datetime.now() + timedelta(days=random.randint(30, 90))
            date_end = date_start + timedelta(days=random.randint(60, 180))
            
            contract = Contract(
                contract_number=contract_number,
                organization_id=org.id,
                date_start=date_start,
                date_end=date_end
            )
            db.session.add(contract)
            print(f"Добавлен договор: {contract_number} (организация: {org.name})")
        contracts[contract_number] = contract
    
    db.session.commit()
    
    # 9. Создание статусов заявок
    status_names = ["0", "1", "2"]  # 0-в ожидании, 1-одобрено, 2-отклонено
    statuses = {}
    
    for name in status_names:
        status = Status.query.filter_by(name=name).first()
        if not status:
            status = Status(name=name)
            db.session.add(status)
            print(f"Добавлен статус: {name}")
        statuses[name] = status
    
    db.session.commit()
    
    # 10. Создание заявок на практику
    for i in range(5):
        # Выбор случайных данных
        student = random.choice([s for s in Student.query.all()])
        practice_type = random.choice(list(practice_types.values()))
        contract = random.choice(list(contracts.values()))
        status = random.choice(list(statuses.values()))
        
        # Руководители
        teacher_role = Role.query.filter_by(name="преподаватель").first()
        teachers = User.query.filter_by(role_id=teacher_role.id).all()
        
        if teachers and len(teachers) >= 2:
            consultant = teachers[0]
            practice_leader = teachers[1]
            
            ask_form = AskForm(
                practice_type=practice_type.id,
                group=student.group_id,
                contract=contract.id,
                ask_form_resposeble=student.id,
                consultant_leader=consultant.id,
                practice_leader=practice_leader.id,
                status=status.id,
                student=student.id
            )
            
            db.session.add(ask_form)
            print(f"Создана заявка на практику для студента {student.surname} {student.name}")
    
    db.session.commit()
    print("База данных успешно заполнена!") 