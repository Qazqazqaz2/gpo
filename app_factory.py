"""
Фабрика приложения GPO My
Централизованная инициализация всех компонентов
"""
import os
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache

from config import config
from extensions import db, migrate, login_manager
# Импортируем модели для регистрации
from models.base import BaseModel
from models.user import User, Role
from models.academic import Student, Group, Direction, Cafedral, PracticTime
from models.practice import PracticeType, AskForm, Status
from models.organization import Organization, Contract
from models.template import Field, Template

# Импортируем сервисы
from services import UserService, StudentService, PracticeService, OrganizationService, PDFService, EmailService


def create_app(config_name=None):
    """Создание экземпляра приложения"""
    
    # Определяем конфигурацию
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Инициализация расширений
    initialize_extensions(app)
    
    # Регистрация blueprints
    register_blueprints(app)
    
    # Настройка обработки ошибок
    register_error_handlers(app)
    
    # Инициализация базы данных
    initialize_database(app)
    
    # Настройка DDoS защиты
    setup_ddos_protection(app)
    
    # Настройка кэширования
    setup_caching(app)
    
    return app


def initialize_extensions(app):
    """Инициализация расширений Flask"""
    
    # SQLAlchemy
    db.init_app(app)
    
    # Flask-Migrate
    migrate.init_app(app, db)
    
    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для доступа к этой странице необходимо войти в систему'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))


def register_blueprints(app):
    """Регистрация blueprints"""
    
    # Импортируем blueprints
    from routes.auth import auth
    from routes.main import main
    from routes.api import api
    
    # Регистрируем blueprints
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(main)
    app.register_blueprint(api, url_prefix='/api')


def register_error_handlers(app):
    """Регистрация обработчиков ошибок"""
    
    from utils.exceptions import ValidationError, BusinessLogicError, NotFoundError
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Неверный запрос'}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Требуется аутентификация'}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Доступ запрещен'}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Страница не найдена'}, 404
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return {'error': 'Слишком много запросов'}, 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return {'error': 'Внутренняя ошибка сервера'}, 500
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return {
            'error': 'Ошибка валидации',
            'message': error.message,
            'field': error.field,
            'errors': error.errors
        }, 400
    
    @app.errorhandler(BusinessLogicError)
    def handle_business_logic_error(error):
        return {
            'error': 'Ошибка бизнес-логики',
            'message': error.message,
            'code': error.code
        }, 422
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        return {
            'error': 'Объект не найден',
            'message': error.message,
            'object_type': error.object_type,
            'object_id': error.object_id
        }, 404


def initialize_database(app):
    """Инициализация базы данных"""
    
    with app.app_context():
        try:
            # Создаем таблицы
            db.create_all()
            
            # Создаем базовые данные, если их нет
            create_default_data()
            
            app.logger.info("Database initialized successfully")
            
        except Exception as e:
            app.logger.error(f"Error initializing database: {e}")
            raise


def add_initial_students():
    """Добавить начальный список студентов 742-1 с паролем 'password'"""
    from services.user_service import UserService
    from services.student_service import StudentService
    
    students_info = [
        {'surname': 'Аристархова', 'name': 'Мария', 'patronymic': 'Дмитриевна'},
        {'surname': 'Белкова', 'name': 'Дана', 'patronymic': 'Руслановна'},
        {'surname': 'Глебов', 'name': 'Лев', 'patronymic': 'Вячеславович'},
        {'surname': 'Долгополов', 'name': 'Владимир', 'patronymic': 'Андреевич'},
        {'surname': 'Егорова', 'name': 'Анастасия', 'patronymic': 'Игоревна'},
        {'surname': 'Едренов', 'name': 'Егор', 'patronymic': 'Владимирович'},
        {'surname': 'Зверков', 'name': 'Роман', 'patronymic': 'Алексеевич'},
        {'surname': 'Исматуллоева', 'name': 'Сабина', 'patronymic': 'Сайфуллоевна'},
        {'surname': 'Канатников', 'name': 'Семён', 'patronymic': 'Дмитриевич'},
        {'surname': 'Карпов', 'name': 'Степан', 'patronymic': 'Евгеньевич'},
        {'surname': 'Карташова', 'name': 'Елизавета', 'patronymic': 'Ивановна'},
        {'surname': 'Корнилов', 'name': 'Данила', 'patronymic': 'Александрович'},
        {'surname': 'Крючков', 'name': 'Максим', 'patronymic': 'Сергеевич'},
        {'surname': 'Лакоза', 'name': 'Талина', 'patronymic': 'Михайловна'},
        {'surname': 'Леоненко', 'name': 'Татьяна', 'patronymic': 'Дмитриевна'},
        {'surname': 'Логунович', 'name': 'Игорь', 'patronymic': 'Вадимович'},
        {'surname': 'Малявский', 'name': 'Ян', 'patronymic': 'Ильич'},
        {'surname': 'Муханов', 'name': 'Андрей', 'patronymic': 'Денисович'},
        {'surname': 'Нимаева', 'name': 'Екатерина', 'patronymic': 'Намсараевна'},
        {'surname': 'Павлова', 'name': 'Арина', 'patronymic': 'Сергеевна'},
        {'surname': 'Плисс', 'name': 'Кирилл', 'patronymic': 'Сергеевич'},
        {'surname': 'Рудникович', 'name': 'Марина', 'patronymic': 'Андреевна'},
        {'surname': 'Синицин', 'name': 'Артём', 'patronymic': 'Валерьевич'},
        {'surname': 'Фищук', 'name': 'Иван', 'patronymic': 'Сергеевич'},
        {'surname': 'Якимовец', 'name': 'Софья', 'patronymic': 'Сергеевна'},
        {'surname': 'Яремчук', 'name': 'Анастасия', 'patronymic': 'Владимировна'},
    ]
    group_name = '742-1'
    password = 'password'

    student_service = StudentService()
    user_service = UserService()

    # Ensure group exists
    group = None
    from models.academic import Group
    group = Group.get_by_name(group_name)
    for s in students_info:
        username = f"{s['surname'].lower()}_{s['name'].lower()}_7421"
        print(f"Adding student: {username}")

    if not group:
        group = student_service._create_default_group(group_name)

    # For each student, create user and student
    for s in students_info:
        username = f"{s['surname'].lower()}_{s['name'].lower()}_7421"
        print(f"Adding student: {username}")
        # Check if user exists
        user = user_service.get_by_username(username)
        if not user:
            user = user_service.create_user(username=username, password=password, role_name='студент')
        # Check if student exists (unique by full name and group)
        from models.academic import Student
        student_exists = Student.query.filter_by(surname=s['surname'], name=s['name'], patronymic=s['patronymic'], group_id=group.id).first()
        if not student_exists:
            student = student_service.create_student(
                name=s['name'],
                surname=s['surname'],
                patronymic=s['patronymic'],
                group_id=group.id
            )


def create_default_data():
    """Создание базовых данных"""
    
    # Создаем роли по умолчанию
    Role.create_default_roles()
    
    # Создаем статусы по умолчанию
    Status.create_default_statuses()
    
    # Создаем кафедру по умолчанию
    if not Cafedral.query.first():
        cafedral = Cafedral(
            name='ФСУ',
            description='Факультет систем управления'
        )
        cafedral.save()
    
    # Создаем направление по умолчанию
    if not Direction.query.first():
        cafedral = Cafedral.query.first()
        direction = Direction(
            name='Программная инженерия',
            code='09.03.04',
            description='Направление подготовки программная инженерия',
            cafedral_id=cafedral.id
        )
        direction.save()
    
    # Создаем группу по умолчанию
    if not Group.query.first():
        direction = Direction.query.first()
        group = Group(
            name='722-1',
            direction_id=direction.id
        )
        group.save()
    
    # Создаем типы практики по умолчанию
    if not PracticeType.query.first():
        practice_types = [
            {'name': 'Учебная практика', 'description': 'Учебная практика', 'duration_days': 14},
            {'name': 'Производственная практика', 'description': 'Производственная практика', 'duration_days': 28},
            {'name': 'Преддипломная практика', 'description': 'Преддипломная практика', 'duration_days': 42}
        ]
        
        for pt_data in practice_types:
            practice_type = PracticeType(**pt_data)
            practice_type.save()

    # После создания групп — добавляем студентов 742-1
    add_initial_students()


def setup_ddos_protection(app):
    """Настройка DDoS защиты"""
    
    try:
        from ddos_protection import protect_flask_app
        
        # Конфигурация DDoS защиты
        ddos_config = {
            "RATE_LIMIT": app.config.get('DDOS_RATE_LIMIT', 150),
            "MAX_CONNECTIONS_PER_IP": app.config.get('DDOS_MAX_CONNECTIONS_PER_IP', 25),
            "BLACKLIST_THRESHOLD": app.config.get('DDOS_BLACKLIST_THRESHOLD', 3),
            "ANOMALY_DETECTION_ENABLED": app.config.get('DDOS_ANOMALY_DETECTION_ENABLED', True),
            "WHITELISTED_IPS": app.config.get('DDOS_WHITELISTED_IPS', {'127.0.0.1', '::1'})
        }
        
        # Применяем защиту
        protect_flask_app(app, ddos_config)
        app.logger.info("DDoS protection configured")
        
    except ImportError:
        app.logger.warning("DDoS protection module not available")
    except Exception as e:
        app.logger.error(f"Error setting up DDoS protection: {e}")


def setup_caching(app):
    """Настройка кэширования"""
    
    try:
        cache = Cache(app)
        app.cache = cache
        app.logger.info("Caching configured")
    except Exception as e:
        app.logger.error(f"Error setting up caching: {e}")


def create_services(app):
    """Создание экземпляров сервисов"""
    
    with app.app_context():
        # Создаем сервисы и добавляем их в контекст приложения
        app.user_service = UserService()
        app.student_service = StudentService()
        app.practice_service = PracticeService()
        app.organization_service = OrganizationService()
        app.pdf_service = PDFService()
        app.email_service = EmailService()
    
    app.logger.info("Services initialized")


def get_app_context():
    """Получение контекста приложения для использования вне Flask"""
    
    from flask import current_app
    return current_app._get_current_object()


# Функция для создания приложения с сервисами
def create_app_with_services(config_name=None):
    """Создание приложения с инициализированными сервисами"""
    
    app = create_app(config_name)
    create_services(app)
    
    return app
