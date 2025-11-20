"""
Сервис для работы с организациями и договорами
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .base_service import BaseService
from models.organization import Organization, Contract
from extensions import db


class OrganizationService(BaseService):
    """Сервис для работы с организациями"""
    
    def __init__(self):
        super().__init__(Organization)
    
    def create_organization(self, name: str, address: str, contact_person: str = None,
                          phone: str = None, email: str = None, website: str = None,
                          description: str = None) -> Optional[Organization]:
        """Создать новую организацию"""
        try:
            # Проверяем, не существует ли уже организация с таким именем
            if self.get_by_name(name):
                raise ValueError(f"Организация с именем {name} уже существует")
            
            organization = Organization(
                name=name,
                address=address,
                contact_person=contact_person,
                phone=phone,
                email=email,
                website=website,
                description=description
            )
            organization.save()
            
            return organization
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_by_name(self, name: str) -> Optional[Organization]:
        """Получить организацию по имени"""
        return Organization.get_by_name(name)
    
    def search_by_name(self, name: str) -> List[Organization]:
        """Поиск организаций по имени"""
        return Organization.search_by_name(name)
    
    def get_active_organizations(self) -> List[Organization]:
        """Получить активные организации"""
        return Organization.get_active()
    
    def get_organization_with_contracts(self, organization_id: int) -> Optional[Dict[str, Any]]:
        """Получить организацию с договорами"""
        organization = self.get_by_id(organization_id)
        if not organization:
            return None
        
        contracts = Contract.query.filter_by(organization_id=organization_id).all()
        
        return {
            'id': organization.id,
            'name': organization.name,
            'address': organization.address,
            'contact_person': organization.contact_person,
            'phone': organization.phone,
            'email': organization.email,
            'website': organization.website,
            'description': organization.description,
            'is_active': organization.is_active,
            'contracts': [
                {
                    'id': contract.id,
                    'contract_number': contract.contract_number,
                    'date_start': contract.date_start.isoformat() if contract.date_start else None,
                    'date_end': contract.date_end.isoformat() if contract.date_end else None,
                    'is_active': contract.is_active,
                    'is_current': contract.is_current,
                    'max_students': contract.max_students,
                    'used_slots': contract.get_used_slots(),
                    'available_slots': contract.get_available_slots()
                } for contract in contracts
            ],
            'created_at': organization.created_at,
            'updated_at': organization.updated_at
        }
    
    def deactivate_organization(self, organization_id: int) -> bool:
        """Деактивировать организацию"""
        try:
            organization = self.get_by_id(organization_id)
            if organization:
                organization.update(is_active=False)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    def activate_organization(self, organization_id: int) -> bool:
        """Активировать организацию"""
        try:
            organization = self.get_by_id(organization_id)
            if organization:
                organization.update(is_active=True)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e


class ContractService(BaseService):
    """Сервис для работы с договорами"""
    
    def __init__(self):
        super().__init__(Contract)
    
    def create_contract(self, contract_number: str, organization_id: int,
                       date_start: datetime = None, date_end: datetime = None,
                       description: str = None, max_students: int = None) -> Optional[Contract]:
        """Создать новый договор"""
        try:
            # Проверяем, не существует ли уже договор с таким номером
            if self.get_by_number(contract_number):
                raise ValueError(f"Договор с номером {contract_number} уже существует")
            
            # Проверяем существование организации
            organization = Organization.get_by_id(organization_id)
            if not organization:
                raise ValueError("Организация не найдена")
            
            contract = Contract(
                contract_number=contract_number,
                organization_id=organization_id,
                date_start=date_start,
                date_end=date_end,
                description=description,
                max_students=max_students
            )
            contract.save()
            
            return contract
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_by_number(self, contract_number: str) -> Optional[Contract]:
        """Получить договор по номеру"""
        return Contract.get_by_number(contract_number)
    
    def get_active_contracts(self) -> List[Contract]:
        """Получить активные договоры"""
        return Contract.get_active()
    
    def get_current_contracts(self) -> List[Contract]:
        """Получить действующие договоры"""
        return Contract.get_current()
    
    def get_expiring_contracts(self, days: int = 30) -> List[Contract]:
        """Получить договоры, истекающие в ближайшие дни"""
        return Contract.get_expiring_soon(days)
    
    def get_contract_with_details(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """Получить договор с подробной информацией"""
        contract = self.get_by_id(contract_id)
        if not contract:
            return None
        
        return {
            'id': contract.id,
            'contract_number': contract.contract_number,
            'organization': {
                'id': contract.organization.id,
                'name': contract.organization.name,
                'address': contract.organization.address
            },
            'date_start': contract.date_start.isoformat() if contract.date_start else None,
            'date_end': contract.date_end.isoformat() if contract.date_end else None,
            'description': contract.description,
            'max_students': contract.max_students,
            'is_active': contract.is_active,
            'is_current': contract.is_current,
            'is_expired': contract.is_expired,
            'days_until_expiry': contract.days_until_expiry,
            'used_slots': contract.get_used_slots(),
            'available_slots': contract.get_available_slots(),
            'has_available_slots': contract.has_available_slots(),
            'created_at': contract.created_at,
            'updated_at': contract.updated_at
        }
    
    def extend_contract(self, contract_id: int, new_end_date: datetime) -> bool:
        """Продлить договор"""
        try:
            contract = self.get_by_id(contract_id)
            if not contract:
                return False
            
            contract.update(date_end=new_end_date)
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def deactivate_contract(self, contract_id: int) -> bool:
        """Деактивировать договор"""
        try:
            contract = self.get_by_id(contract_id)
            if contract:
                contract.update(is_active=False)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    def activate_contract(self, contract_id: int) -> bool:
        """Активировать договор"""
        try:
            contract = self.get_by_id(contract_id)
            if contract:
                contract.update(is_active=True)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_contracts_by_organization(self, organization_id: int) -> List[Contract]:
        """Получить договоры организации"""
        return Contract.query.filter_by(organization_id=organization_id).all()
    
    def get_available_contracts(self) -> List[Contract]:
        """Получить доступные договоры (текущие с доступными слотами)"""
        current_contracts = self.get_current_contracts()
        return [contract for contract in current_contracts if contract.has_available_slots()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику договоров"""
        total_contracts = self.count()
        active_contracts = len(self.get_active_contracts())
        current_contracts = len(self.get_current_contracts())
        expiring_contracts = len(self.get_expiring_contracts(30))
        
        # Статистика по организациям
        organizations = Organization.get_all()
        org_stats = []
        for org in organizations:
            contracts = self.get_contracts_by_organization(org.id)
            org_stats.append({
                'organization_name': org.name,
                'contracts_count': len(contracts),
                'active_contracts': len([c for c in contracts if c.is_active])
            })
        
        return {
            'total': total_contracts,
            'active': active_contracts,
            'current': current_contracts,
            'expiring_soon': expiring_contracts,
            'organizations': org_stats
        }













