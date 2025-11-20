"""
Вспомогательные функции
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import secrets
import string
from werkzeug.security import generate_password_hash, check_password_hash


def format_date(date_obj: datetime, format_str: str = '%d.%m.%Y') -> str:
    """Форматирование даты"""
    if not date_obj:
        return ''
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except ValueError:
            return date_obj
    
    return date_obj.strftime(format_str)


def format_datetime(datetime_obj: datetime, format_str: str = '%d.%m.%Y %H:%M') -> str:
    """Форматирование даты и времени"""
    if not datetime_obj:
        return ''
    
    if isinstance(datetime_obj, str):
        try:
            datetime_obj = datetime.fromisoformat(datetime_obj.replace('Z', '+00:00'))
        except ValueError:
            return datetime_obj
    
    return datetime_obj.strftime(format_str)


def generate_password(length: int = 12, include_symbols: bool = True) -> str:
    """Генерация случайного пароля"""
    characters = string.ascii_letters + string.digits
    if include_symbols:
        characters += '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    return ''.join(secrets.choice(characters) for _ in range(length))


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password: str, password_hash: str) -> bool:
    """Проверка пароля"""
    return check_password_hash(password_hash, password)


def generate_username(first_name: str, last_name: str, middle_name: str = None) -> str:
    """Генерация имени пользователя на основе ФИО"""
    # Берем первую букву имени и фамилию
    username = f"{first_name[0].lower()}{last_name.lower()}"
    
    if middle_name:
        # Добавляем первую букву отчества
        username += f"{middle_name[0].lower()}"
    
    return username


def generate_student_id(year: int = None) -> str:
    """Генерация номера студенческого билета"""
    if not year:
        year = datetime.now().year
    
    # Простая генерация: год + случайное число
    import random
    random_part = random.randint(1000, 9999)
    return f"{year}{random_part}"


def format_phone(phone: str) -> str:
    """Форматирование номера телефона"""
    if not phone:
        return ''
    
    # Убираем все нецифровые символы
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) == 11 and digits.startswith('7'):
        # Формат: +7 (XXX) XXX-XX-XX
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        # Формат: +7 (XXX) XXX-XX-XX
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    
    return phone


def parse_phone(phone: str) -> str:
    """Парсинг номера телефона (убираем форматирование)"""
    if not phone:
        return ''
    
    # Убираем все нецифровые символы
    digits = ''.join(filter(str.isdigit, phone))
    
    # Если номер начинается с 8, заменяем на 7
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    
    return digits


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Обрезание текста"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def capitalize_words(text: str) -> str:
    """Заглавные буквы в начале каждого слова"""
    if not text:
        return ''
    
    return ' '.join(word.capitalize() for word in text.split())


def extract_initials(full_name: str) -> str:
    """Извлечение инициалов из полного имени"""
    if not full_name:
        return ''
    
    words = full_name.split()
    if len(words) < 2:
        return full_name
    
    # Первое слово - фамилия, остальные - имя и отчество
    surname = words[0]
    initials = ''.join(word[0].upper() + '.' for word in words[1:])
    
    return f"{surname} {initials}"


def get_age_from_birthdate(birthdate: datetime) -> int:
    """Вычисление возраста по дате рождения"""
    if not birthdate:
        return 0
    
    today = datetime.now().date()
    if isinstance(birthdate, datetime):
        birthdate = birthdate.date()
    
    age = today.year - birthdate.year
    if today.month < birthdate.month or (today.month == birthdate.month and today.day < birthdate.day):
        age -= 1
    
    return age


def is_valid_email(email: str) -> bool:
    """Проверка валидности email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def clean_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    import re
    # Убираем недопустимые символы
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Убираем лишние пробелы и точки
    filename = re.sub(r'\s+', '_', filename.strip('.'))
    return filename


def get_file_extension(filename: str) -> str:
    """Получение расширения файла"""
    if not filename or '.' not in filename:
        return ''
    
    return filename.split('.')[-1].lower()


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    if size_bytes == 0:
        return '0 B'
    
    size_names = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def generate_random_string(length: int = 8) -> str:
    """Генерация случайной строки"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Маскирование чувствительных данных"""
    if not data or len(data) <= visible_chars:
        return '*' * len(data) if data else ''
    
    return data[:visible_chars] + '*' * (len(data) - visible_chars)


def parse_date_range(date_range: str) -> tuple:
    """Парсинг диапазона дат"""
    if not date_range or ' - ' not in date_range:
        return None, None
    
    try:
        start_str, end_str = date_range.split(' - ')
        start_date = datetime.strptime(start_str.strip(), '%d.%m.%Y')
        end_date = datetime.strptime(end_str.strip(), '%d.%m.%Y')
        return start_date, end_date
    except ValueError:
        return None, None


def get_pagination_info(page: int, per_page: int, total: int) -> Dict[str, Any]:
    """Получение информации о пагинации"""
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return {
        'current_page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': page - 1 if has_prev else None,
        'next_page': page + 1 if has_next else None
    }


def safe_int(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = '') -> str:
    """Безопасное преобразование в строку"""
    try:
        return str(value) if value is not None else default
    except (ValueError, TypeError):
        return default

