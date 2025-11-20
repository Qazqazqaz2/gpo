"""
Сервис для работы со студентами
"""
from typing import Optional, List, Dict, Any
from .base_service import BaseService
from models.academic import Student, Group, Direction, Cafedral
from models.user import User
from extensions import db


class StudentService(BaseService):
    """Сервис для работы со студентами"""
    
    def __init__(self):
        super().__init__(Student)
    
    def create_student(self, name: str, surname: str, patronymic: str = None,
                     student_id: str = None, email: str = None, phone: str = None,
                     group_name: str = None, group_id: int = None) -> Optional[Student]:
        """Создать нового студента"""
        try:
            # Определяем группу
            if group_id:
                group = Group.get_by_id(group_id)
            elif group_name:
                group = Group.get_by_name(group_name)
                if not group:
                    # Создаем группу, если её нет
                    group = self._create_default_group(group_name)
            else:
                raise ValueError("Необходимо указать группу")
            
            if not group:
                raise ValueError("Группа не найдена")
            
            # Создаем студента
            student = Student(
                name=name,
                surname=surname,
                patronymic=patronymic,
                student_id=student_id,
                email=email,
                phone=phone,
                group_id=group.id
            )
            student.save()
            
            return student
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _create_default_group(self, group_name: str) -> Group:
        """Создать группу по умолчанию"""
        # Создаем кафедру, если её нет
        cafedral = Cafedral.get_by_name('ФСУ')
        if not cafedral:
            cafedral = Cafedral(name='ФСУ', description='Факультет систем управления')
            cafedral.save()
        
        # Создаем направление, если его нет
        direction = Direction.get_by_name('Программная инженерия')
        if not direction:
            direction = Direction(
                name='Программная инженерия',
                code='09.03.04',
                description='Направление подготовки программная инженерия',
                cafedral_id=cafedral.id
            )
            direction.save()
        
        # Создаем группу
        group = Group(
            name=group_name,
            direction_id=direction.id
        )
        group.save()
        
        return group
    
    def get_by_student_id(self, student_id: str) -> Optional[Student]:
        """Получить студента по номеру студенческого билета"""
        return Student.get_by_student_id(student_id)
    
    def get_by_group(self, group_id: int) -> List[Student]:
        """Получить студентов группы"""
        return Student.get_by_group(group_id)
    
    def get_by_group_name(self, group_name: str) -> List[Student]:
        """Получить студентов группы по имени"""
        group = Group.get_by_name(group_name)
        if group:
            return self.get_by_group(group.id)
        return []
    
    def search_by_name(self, name: str) -> List[Student]:
        """Поиск студентов по имени"""
        return Student.search_by_name(name)
    
    def get_student_with_group_info(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Получить студента с информацией о группе"""
        student = self.get_by_id(student_id)
        if not student:
            return None
        
        return {
            'id': student.id,
            'name': student.name,
            'surname': student.surname,
            'patronymic': student.patronymic,
            'full_name': student.full_name,
            'student_id': student.student_id,
            'email': student.email,
            'phone': student.phone,
            'group': {
                'id': student.group.id,
                'name': student.group.name,
                'direction': {
                    'id': student.group.direction.id,
                    'name': student.group.direction.name,
                    'code': student.group.direction.code
                } if student.group.direction else None
            } if student.group else None,
            'created_at': student.created_at,
            'updated_at': student.updated_at
        }
    
    def update_student_info(self, student_id: int, **kwargs) -> Optional[Student]:
        """Обновить информацию о студенте"""
        try:
            student = self.get_by_id(student_id)
            if not student:
                return None
            
            # Проверяем уникальность student_id, если он изменяется
            if 'student_id' in kwargs and kwargs['student_id']:
                existing_student = self.get_by_student_id(kwargs['student_id'])
                if existing_student and existing_student.id != student_id:
                    raise ValueError(f"Студент с номером {kwargs['student_id']} уже существует")
            
            student.update(**kwargs)
            return student
        except Exception as e:
            db.session.rollback()
            raise e
    
    def transfer_to_group(self, student_id: int, new_group_id: int) -> bool:
        """Перевести студента в другую группу"""
        try:
            student = self.get_by_id(student_id)
            if not student:
                return False
            
            new_group = Group.get_by_id(new_group_id)
            if not new_group:
                return False
            
            student.update(group_id=new_group_id)
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_students_by_direction(self, direction_id: int) -> List[Student]:
        """Получить студентов по направлению"""
        groups = Group.get_by_direction(direction_id)
        students = []
        for group in groups:
            students.extend(self.get_by_group(group.id))
        return students
    
    def get_student_stats(self) -> Dict[str, Any]:
        """Получить статистику студентов"""
        total_students = self.count()
        
        # Статистика по группам
        groups = Group.get_all()
        group_stats = []
        for group in groups:
            students_count = len(self.get_by_group(group.id))
            group_stats.append({
                'group_name': group.name,
                'students_count': students_count,
                'direction': group.direction.name if group.direction else None
            })
        
        # Статистика по направлениям
        directions = Direction.get_all()
        direction_stats = []
        for direction in directions:
            students_count = len(self.get_students_by_direction(direction.id))
            direction_stats.append({
                'direction_name': direction.name,
                'students_count': students_count
            })
        
        return {
            'total_students': total_students,
            'groups': group_stats,
            'directions': direction_stats
        }
    
    def create_user_for_student(self, student_id: int, username: str, password: str) -> Optional[User]:
        """Создать пользователя для студента"""
        try:
            student = self.get_by_id(student_id)
            if not student:
                return None
            
            # Создаем пользователя
            from services.user_service import UserService
            user_service = UserService()
            
            user = user_service.create_user(
                username=username,
                password=password,
                email=student.email,
                role_name='студент'
            )
            
            return user
        except Exception as e:
            db.session.rollback()
            raise e













