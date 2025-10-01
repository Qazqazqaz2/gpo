from app import app
from extensions import db
from models import User, Student, Group

with app.app_context():
    # Get the user qaqq
    user = User.query.filter_by(username='qaqq').first()
    if not user:
        print("User 'qaqq' not found. Please register this user first.")
        exit()
    
    # Get group 722-1
    group = Group.query.filter_by(name='722-1').first()
    if not group:
        print("Group '722-1' not found. Please run create_defaults.py first.")
        exit()
    
    # Check if student record already exists
    student = Student.query.filter_by(name=user.username).first()
    if student:
        # Update existing student record
        student.group_id = group.id
        print(f"Updated existing student record for {user.username} with group 722-1")
    else:
        # Create new student record
        student = Student(
            name=user.username,
            surname=user.username,  # Using username as surname as well
            patronymic="",  # Empty patronymic
            group_id=group.id
        )
        db.session.add(student)
        print(f"Created new student record for {user.username} with group 722-1")
    
    db.session.commit()
    print("Done!") 