from flask import Flask, render_template, request, redirect, url_for, flash
import os
from dotenv import load_dotenv
from extensions import db, migrate, login_manager
from models import User, Role
from ddos_protection import protect_flask_app, rate_limit, geo_filter

# Load environment variables from .env if present
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Core config from environment
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_change_in_production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:762341@localhost/gpo_practice')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)

# Configure DDoS protection with env-driven settings
ddos_config = {
    "RATE_LIMIT": int(os.getenv('DDOS_RATE_LIMIT', '150')),
    "MAX_CONNECTIONS_PER_IP": int(os.getenv('DDOS_MAX_CONNECTIONS_PER_IP', '25')),
    "BLACKLIST_THRESHOLD": int(os.getenv('DDOS_BLACKLIST_THRESHOLD', '3')),
    "ANOMALY_DETECTION_ENABLED": os.getenv('DDOS_ANOMALY_DETECTION_ENABLED', 'True').lower() == 'true',
    "WHITELISTED_IPS": set(ip.strip() for ip in os.getenv('DDOS_WHITELISTED_IPS', '127.0.0.1,::1').split(',')),
}

# Apply DDoS protection to the app
cache = protect_flask_app(app, ddos_config)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import routes
from routes.auth import auth
from routes.main import main

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(main)

# Create tables
with app.app_context():
    try:
        db.create_all()
        # Create default roles if they don't exist
        if not Role.query.filter_by(name='студент').first():
            student_role = Role(name='студент')
            db.session.add(student_role)
        if not Role.query.filter_by(name='преподаватель').first():
            teacher_role = Role(name='преподаватель')
            db.session.add(teacher_role)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error during database initialization: {e}")

# Main route
@app.route('/')
@rate_limit()  # Apply rate limiting to this route
def index():
    return render_template('index.html')

# Student dashboard - needs additional protection
@app.route('/student/dashboard')
@rate_limit()
@geo_filter()  # Add geo-filtering to protect student access
def student_dashboard():
    return render_template('student_dashboard.html')

# Practice form - apply caching and rate limiting
@app.route('/practice/form', methods=['GET', 'POST'])
@rate_limit()
def practice_form():
    if request.method == 'POST':
        # Process form submission
        flash('Заявка успешно отправлена!', 'success')
        return redirect(url_for('student_dashboard'))
    
    # Example data for template - in a real app, this would come from a database
    context = {
        'practice_types': [{'id': 1, 'name': 'Учебная практика'}, {'id': 2, 'name': 'Производственная практика'}],
        'groups': [{'id': 1, 'name': 'Группа 101'}, {'id': 2, 'name': 'Группа 102'}],
        'contracts': [{'id': 1, 'contract_number': 'Договор №123'}, {'id': 2, 'contract_number': 'Договор №456'}],
        'teachers': [{'id': 1, 'username': 'Иванов И.И.'}, {'id': 2, 'username': 'Петров П.П.'}],
        'default_group': {'id': 1, 'name': 'Группа 101'},
    }
    
    return render_template('practice_form.html', **context)

# API endpoints should have strict protections
@app.route('/api/data')
@rate_limit()
@geo_filter()
def api_data():
    return {"status": "success", "message": "API access allowed"}

if __name__ == '__main__':
    app.run(debug=False)