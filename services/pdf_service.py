"""
Сервис для генерации PDF документов
"""
from typing import Optional, Dict, Any
import os
import tempfile
from io import BytesIO
from datetime import datetime
from flask import current_app
from models.practice import AskForm
from models.academic import Student, Group
from models.organization import Contract, Organization
from models.user import User
from test_pdf import process_template


class PDFService:
    """Сервис для генерации PDF документов"""
    
    def __init__(self):
        self.template_path = None
        self.output_folder = None
    
    def set_template_path(self, template_path: str):
        """Установить путь к шаблону"""
        self.template_path = template_path
    
    def set_output_folder(self, output_folder: str):
        """Установить папку для сохранения PDF"""
        self.output_folder = output_folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)
    
    def generate_practice_application_pdf(self, application_id: int, 
                                        custom_data: Dict[str, Any] = None) -> Optional[bytes]:
        """Генерация PDF заявки на практику"""
        try:
            # Получаем заявку
            application = AskForm.get_by_id(application_id)
            if not application:
                raise ValueError("Заявка не найдена")
            
            # Подготавливаем данные для заполнения шаблона
            data = self._prepare_application_data(application, custom_data)
            
            # Определяем путь к шаблону
            template_path = self.template_path or self._get_default_template_path()
            
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Шаблон не найден: {template_path}")
            
            # Генерируем PDF
            pdf_data = process_template(template_path, data)
            
            # Если возвращается путь к файлу, читаем его содержимое
            if isinstance(pdf_data, str):
                with open(pdf_data, 'rb') as f:
                    return f.read()
            
            # Иначе возвращаем данные напрямую
            return pdf_data
            
        except Exception as e:
            current_app.logger.error(f"Ошибка генерации PDF: {str(e)}")
            raise e
    
    def _prepare_application_data(self, application: AskForm, custom_data: Dict[str, Any] = None) -> Dict[str, str]:
        """Подготовка данных для заполнения шаблона"""
        # Базовые данные из заявки
        student = application.student
        group = application.group
        contract = application.contract
        organization = contract.organization
        practice_leader = application.practice_leader_user
        
        # Формируем полное имя студента
        full_student_name = student.full_name
        
        # Получаем номер телефона и email
        phone_number = application.phone_number or student.phone or '+7XXXXXXXXXX'
        email = application.email or student.email or 'student@example.com'
        
        # Получаем название организации
        organization_name = organization.name
        organization_address = organization.address
        
        # Получаем имя руководителя практики
        practice_leader_name = practice_leader.username if practice_leader else 'Не указан'
        
        # Текущая дата
        today_date = datetime.now().strftime('%d.%m.%Y')
        
        # Базовые данные
        data = {
            'ГРУППА0': group.name if group else 'Не указана',
            'ФИОСТУДЕНТА': full_student_name,
            'НОМЕРСТУДЕНТА': phone_number,
            'МАИЛ': email,
            'ОРГАНИЗАЦИЯ': organization_name,
            'АДРЕС': organization_address,
            'РУКОВОДИТЕЛЬ': practice_leader_name,
            'ДАТА': today_date
        }
        
        # Добавляем пользовательские данные, если они предоставлены
        if custom_data:
            data.update(custom_data)
        
        return data
    
    def _get_default_template_path(self) -> str:
        """Получить путь к шаблону по умолчанию"""
        return os.path.join(current_app.root_path, 'ShABLON_732_grupp_Zayavlenie_na_prokhozhdenie_praktiki-1.docx')
    
    def save_pdf_to_file(self, pdf_data: bytes, filename: str = None) -> str:
        """Сохранить PDF в файл"""
        try:
            # Определяем имя файла
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'practice_application_{timestamp}.pdf'
            
            # Определяем папку для сохранения
            output_folder = self.output_folder or current_app.config.get('PDF_OUTPUT_FOLDER', 'generated_pdfs')
            if not os.path.exists(output_folder):
                os.makedirs(output_folder, exist_ok=True)
            
            # Полный путь к файлу
            file_path = os.path.join(output_folder, filename)
            
            # Сохраняем файл
            with open(file_path, 'wb') as f:
                f.write(pdf_data)
            
            return file_path
            
        except Exception as e:
            current_app.logger.error(f"Ошибка сохранения PDF: {str(e)}")
            raise e
    
    def generate_and_save_pdf(self, application_id: int, filename: str = None, 
                            custom_data: Dict[str, Any] = None) -> str:
        """Генерировать и сохранить PDF"""
        try:
            # Генерируем PDF
            pdf_data = self.generate_practice_application_pdf(application_id, custom_data)
            
            # Сохраняем в файл
            file_path = self.save_pdf_to_file(pdf_data, filename)
            
            return file_path
            
        except Exception as e:
            current_app.logger.error(f"Ошибка генерации и сохранения PDF: {str(e)}")
            raise e
    
    def get_pdf_as_bytesio(self, application_id: int, custom_data: Dict[str, Any] = None) -> BytesIO:
        """Получить PDF как BytesIO объект"""
        try:
            pdf_data = self.generate_practice_application_pdf(application_id, custom_data)
            return BytesIO(pdf_data)
        except Exception as e:
            current_app.logger.error(f"Ошибка создания BytesIO: {str(e)}")
            raise e
    
    def validate_template(self, template_path: str = None) -> bool:
        """Проверить существование и доступность шаблона"""
        try:
            path = template_path or self._get_default_template_path()
            return os.path.exists(path) and os.access(path, os.R_OK)
        except Exception:
            return False
    
    def get_template_info(self, template_path: str = None) -> Dict[str, Any]:
        """Получить информацию о шаблоне"""
        try:
            path = template_path or self._get_default_template_path()
            
            if not os.path.exists(path):
                return {'exists': False, 'error': 'Файл не найден'}
            
            stat = os.stat(path)
            return {
                'exists': True,
                'path': path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'readable': os.access(path, os.R_OK)
            }
        except Exception as e:
            return {'exists': False, 'error': str(e)}
    
    def cleanup_old_pdfs(self, days: int = 7) -> int:
        """Очистить старые PDF файлы"""
        try:
            output_folder = self.output_folder or current_app.config.get('PDF_OUTPUT_FOLDER', 'generated_pdfs')
            
            if not os.path.exists(output_folder):
                return 0
            
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            deleted_count = 0
            
            for filename in os.listdir(output_folder):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(output_folder, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            current_app.logger.error(f"Ошибка очистки старых PDF: {str(e)}")
            return 0













