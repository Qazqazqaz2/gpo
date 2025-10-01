from app import app
from extensions import db
from models import User, Organization, Contract, Student, Group
from datetime import datetime, timedelta
import random

with app.app_context():
    # Check if user Артемка exists
    user = User.query.filter_by(username='Артемка').first()
    if not user:
        print("Пользователь 'Артемка' не найден. Используем существующие данные.")
    
    # Make sure we have organizations
    organizations = Organization.query.all()
    if not organizations:
        # Create a default organization if none exists
        default_org = Organization(name="ТУСУР", address="г. Томск, пр. Ленина, 40")
        db.session.add(default_org)
        db.session.commit()
        organizations = [default_org]
    
    # Create sample contract data
    contract_numbers = [
        '1232321',  # The one from the example
        'ДОГ-2025-001',
        'ПРК-2025-002',
        'СТЖ-2025-003',
        'ДП-2025-123'
    ]
    
    # Current date and some random future dates
    now = datetime.now()
    
    # Add contracts
    for i, contract_number in enumerate(contract_numbers):
        # Check if contract already exists
        existing_contract = Contract.query.filter_by(contract_number=contract_number).first()
        if existing_contract:
            print(f"Контракт {contract_number} уже существует, пропускаем.")
            continue
        
        # Random organization from the available ones
        org = random.choice(organizations)
        
        # Random dates (1-3 months from now for start, 3-6 months from now for end)
        date_start = now + timedelta(days=random.randint(30, 90))
        date_end = date_start + timedelta(days=random.randint(60, 180))
        
        # Create new contract
        new_contract = Contract(
            contract_number=contract_number,
            organization_id=org.id,
            date_start=date_start,
            date_end=date_end
        )
        
        db.session.add(new_contract)
        print(f"Добавлен контракт {contract_number} с организацией {org.name}")
    
    # Commit all changes
    db.session.commit()
    print("Данные успешно добавлены в таблицу contracts!") 