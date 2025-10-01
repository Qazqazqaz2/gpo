from app import app
from extensions import db
from models import PracticeType, User, Organization, Contract, Role, Direction, Cafedral, Group, Status

# Flask application context
with app.app_context():
    # Add practice types
    practice_types = ["Учебная", "Преддепломная", "Производственная"]
    for practice_type in practice_types:
        if not PracticeType.query.filter_by(name=practice_type).first():
            db.session.add(PracticeType(name=practice_type))
    
    # Add teacher role
    teacher_role = Role.query.filter_by(name='преподаватель').first()
    if not teacher_role:
        teacher_role = Role(name='преподаватель')
        db.session.add(teacher_role)
        db.session.commit()
    
    # Add default teachers
    leaders = ["Руководитель П. П.", "Руководитель Р. Р."]
    for leader in leaders:
        if not User.query.filter_by(username=leader).first():
            new_teacher = User(username=leader, role_id=teacher_role.id)
            new_teacher.set_password("password")  # Default password
            db.session.add(new_teacher)
    
    # Add default organization for contracts
    default_org = Organization.query.filter_by(name="ТУСУР").first()
    if not default_org:
        default_org = Organization(name="ТУСУР", address="г. Томск, пр. Ленина, 40")
        db.session.add(default_org)
        db.session.commit()
    
    # Add default contracts
    contract_types = ["Заявление", "Договор"]
    for contract_type in contract_types:
        if not Contract.query.filter_by(contract_number=contract_type).first():
            db.session.add(Contract(
                contract_number=contract_type,
                organization_id=default_org.id
            ))
            
    # Add default cafedral, direction and group
    default_cafedral = Cafedral.query.filter_by(name="ФСУ").first()
    if not default_cafedral:
        default_cafedral = Cafedral(name="ФСУ")
        db.session.add(default_cafedral)
        db.session.commit()
        
    default_direction = Direction.query.filter_by(name="Программная инженерия").first()
    if not default_direction:
        default_direction = Direction(name="Программная инженерия", cafedral_id=default_cafedral.id)
        db.session.add(default_direction)
        db.session.commit()
    
    # Add default group
    default_group = Group.query.filter_by(name="722-1").first()
    if not default_group:
        default_group = Group(name="722-1", direction_id=default_direction.id)
        db.session.add(default_group)
        
    # Create default statuses
    statuses = ["0", "1", "2"]  # 0-pending, 1-approved, 2-rejected
    for status_name in statuses:
        if not Status.query.filter_by(name=status_name).first():
            db.session.add(Status(name=status_name))
    
    db.session.commit()
    print("Default values added to database successfully.") 