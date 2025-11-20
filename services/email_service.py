"""
Сервис для отправки email уведомлений
"""
from typing import Optional, List, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app
from models.user import User
from models.practice import AskForm


class EmailService:
    """Сервис для отправки email уведомлений"""
    
    def __init__(self):
        # Получаем конфигурацию с значениями по умолчанию
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.smtp_username = None
        self.smtp_password = None
        self.from_email = 'noreply@gpo.ru'
        self.from_name = 'GPO My'
        
        # Обновляем конфигурацию, если доступен контекст приложения
        try:
            from flask import current_app
            self.smtp_server = current_app.config.get('SMTP_SERVER', self.smtp_server)
            self.smtp_port = current_app.config.get('SMTP_PORT', self.smtp_port)
            self.smtp_username = current_app.config.get('SMTP_USERNAME', self.smtp_username)
            self.smtp_password = current_app.config.get('SMTP_PASSWORD', self.smtp_password)
            self.from_email = current_app.config.get('FROM_EMAIL', self.from_email)
            self.from_name = current_app.config.get('FROM_NAME', self.from_name)
        except RuntimeError:
            # Работаем вне контекста приложения, используем значения по умолчанию
            pass
    
    def send_email(self, to_email: str, subject: str, body: str, 
                  html_body: str = None, attachments: List[str] = None) -> bool:
        """Отправить email"""
        try:
            if not self.smtp_username or not self.smtp_password:
                current_app.logger.warning("SMTP credentials not configured, email not sent")
                return False
            
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Добавляем текстовую часть
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Добавляем HTML часть, если есть
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Добавляем вложения
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)
            
            # Отправляем email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            current_app.logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Добавить файл как вложение"""
        try:
            with open(file_path, 'rb') as f:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {file_path.split("/")[-1]}'
                )
                msg.attach(attachment)
        except Exception as e:
            current_app.logger.error(f"Error attaching file {file_path}: {str(e)}")
    
    def send_application_notification(self, application_id: int, notification_type: str) -> bool:
        """Отправить уведомление о заявке"""
        try:
            application = AskForm.get_by_id(application_id)
            if not application:
                return False
            
            # Получаем email адреса
            student_email = application.email or application.student.email
            teacher_emails = self._get_teacher_emails(application)
            
            if notification_type == 'created':
                return self._send_application_created_notification(application, student_email, teacher_emails)
            elif notification_type == 'approved':
                return self._send_application_approved_notification(application, student_email)
            elif notification_type == 'rejected':
                return self._send_application_rejected_notification(application, student_email)
            elif notification_type == 'in_progress':
                return self._send_application_in_progress_notification(application, student_email)
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error sending application notification: {str(e)}")
            return False
    
    def _get_teacher_emails(self, application: AskForm) -> List[str]:
        """Получить email адреса преподавателей"""
        emails = []
        
        if application.consultant_user and application.consultant_user.email:
            emails.append(application.consultant_user.email)
        
        if application.practice_leader_user and application.practice_leader_user.email:
            emails.append(application.practice_leader_user.email)
        
        return list(set(emails))  # Убираем дубликаты
    
    def _send_application_created_notification(self, application: AskForm, 
                                           student_email: str, teacher_emails: List[str]) -> bool:
        """Отправить уведомление о создании заявки"""
        subject = "Новая заявка на практику"
        
        body = f"""
Здравствуйте!

Создана новая заявка на практику:

Студент: {application.student.full_name}
Группа: {application.student.group.name if application.student.group else 'Не указана'}
Тип практики: {application.practice_type.name}
Организация: {application.contract.organization.name}

Заявка находится на рассмотрении.

С уважением,
Система GPO My
        """
        
        html_body = f"""
        <html>
        <body>
        <h2>Новая заявка на практику</h2>
        <p>Создана новая заявка на практику:</p>
        <ul>
        <li><strong>Студент:</strong> {application.student.full_name}</li>
        <li><strong>Группа:</strong> {application.student.group.name if application.student.group else 'Не указана'}</li>
        <li><strong>Тип практики:</strong> {application.practice_type.name}</li>
        <li><strong>Организация:</strong> {application.contract.organization.name}</li>
        </ul>
        <p>Заявка находится на рассмотрении.</p>
        <p>С уважением,<br>Система GPO My</p>
        </body>
        </html>
        """
        
        # Отправляем студенту
        if student_email:
            self.send_email(student_email, subject, body, html_body)
        
        # Отправляем преподавателям
        for teacher_email in teacher_emails:
            self.send_email(teacher_email, subject, body, html_body)
        
        return True
    
    def _send_application_approved_notification(self, application: AskForm, student_email: str) -> bool:
        """Отправить уведомление об одобрении заявки"""
        if not student_email:
            return False
        
        subject = "Заявка на практику одобрена"
        
        body = f"""
Здравствуйте, {application.student.full_name}!

Ваша заявка на практику одобрена.

Детали заявки:
- Тип практики: {application.practice_type.name}
- Организация: {application.contract.organization.name}
- Руководитель практики: {application.practice_leader_user.username if application.practice_leader_user else 'Не указан'}

Поздравляем!

С уважением,
Система GPO My
        """
        
        html_body = f"""
        <html>
        <body>
        <h2>Заявка на практику одобрена</h2>
        <p>Здравствуйте, {application.student.full_name}!</p>
        <p>Ваша заявка на практику одобрена.</p>
        <ul>
        <li><strong>Тип практики:</strong> {application.practice_type.name}</li>
        <li><strong>Организация:</strong> {application.contract.organization.name}</li>
        <li><strong>Руководитель практики:</strong> {application.practice_leader_user.username if application.practice_leader_user else 'Не указан'}</li>
        </ul>
        <p>Поздравляем!</p>
        <p>С уважением,<br>Система GPO My</p>
        </body>
        </html>
        """
        
        return self.send_email(student_email, subject, body, html_body)
    
    def _send_application_rejected_notification(self, application: AskForm, student_email: str) -> bool:
        """Отправить уведомление об отклонении заявки"""
        if not student_email:
            return False
        
        subject = "Заявка на практику отклонена"
        
        body = f"""
Здравствуйте, {application.student.full_name}!

К сожалению, ваша заявка на практику отклонена.

Детали заявки:
- Тип практики: {application.practice_type.name}
- Организация: {application.contract.organization.name}

Причина отклонения: {application.comments or 'Не указана'}

Вы можете подать новую заявку.

С уважением,
Система GPO My
        """
        
        html_body = f"""
        <html>
        <body>
        <h2>Заявка на практику отклонена</h2>
        <p>Здравствуйте, {application.student.full_name}!</p>
        <p>К сожалению, ваша заявка на практику отклонена.</p>
        <ul>
        <li><strong>Тип практики:</strong> {application.practice_type.name}</li>
        <li><strong>Организация:</strong> {application.contract.organization.name}</li>
        </ul>
        <p><strong>Причина отклонения:</strong> {application.comments or 'Не указана'}</p>
        <p>Вы можете подать новую заявку.</p>
        <p>С уважением,<br>Система GPO My</p>
        </body>
        </html>
        """
        
        return self.send_email(student_email, subject, body, html_body)
    
    def _send_application_in_progress_notification(self, application: AskForm, student_email: str) -> bool:
        """Отправить уведомление о том, что заявка в процессе"""
        if not student_email:
            return False
        
        subject = "Заявка на практику в процессе"
        
        body = f"""
Здравствуйте, {application.student.full_name}!

Ваша заявка на практику находится в процессе обработки.

Детали заявки:
- Тип практики: {application.practice_type.name}
- Организация: {application.contract.organization.name}

Мы уведомим вас о результатах.

С уважением,
Система GPO My
        """
        
        html_body = f"""
        <html>
        <body>
        <h2>Заявка на практику в процессе</h2>
        <p>Здравствуйте, {application.student.full_name}!</p>
        <p>Ваша заявка на практику находится в процессе обработки.</p>
        <ul>
        <li><strong>Тип практики:</strong> {application.practice_type.name}</li>
        <li><strong>Организация:</strong> {application.contract.organization.name}</li>
        </ul>
        <p>Мы уведомим вас о результатах.</p>
        <p>С уважением,<br>Система GPO My</p>
        </body>
        </html>
        """
        
        return self.send_email(student_email, subject, body, html_body)
    
    def send_bulk_notification(self, recipients: List[str], subject: str, 
                             body: str, html_body: str = None) -> Dict[str, bool]:
        """Отправить массовое уведомление"""
        results = {}
        
        for email in recipients:
            results[email] = self.send_email(email, subject, body, html_body)
        
        return results
    
    def test_email_configuration(self) -> bool:
        """Проверить конфигурацию email"""
        try:
            if not self.smtp_username or not self.smtp_password:
                return False
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Email configuration test failed: {str(e)}")
            return False
