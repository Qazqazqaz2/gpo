"""
Новое приложение GPO My с улучшенной архитектурой
"""
import os
from app_factory import create_app_with_services

# Создаем приложение
app = create_app_with_services()

# Настройка для разработки
if __name__ == '__main__':
    # Определяем конфигурацию
    config_name = os.getenv('FLASK_ENV', 'development')
    
    # Настройки для разработки
    if config_name == 'development':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # Для продакшена используем WSGI сервер
        app.run(debug=False, host='0.0.0.0', port=5000)
