from flask import Flask, render_template, request, redirect, url_for, flash
import os
from extensions import db, migrate, login_manager
from models import User, Role
from ddos_protection import protect_flask_app, rate_limit, geo_filter

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SECRET_KEY'] = 'dev_key_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:762341@localhost/gpo_practice'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)

# Configure DDoS protection with custom settings
ddos_config = {
    "RATE_LIMIT": 150,                # Allow 150 requests per minute per IP
    "MAX_CONNECTIONS_PER_IP": 25,     # Allow 25 concurrent connections per IP
    "BLACKLIST_THRESHOLD": 3,         # Blacklist after 3 violations
    "ANOMALY_DETECTION_ENABLED": True,
    "WHITELISTED_IPS": set(['127.0.0.1', '::1']),  # Whitelist localhost
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
    # In production, use a proper WSGI server with these settings:
    # For gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 --backlog 1024 app:app
    # For uWSGI: uwsgi --socket 0.0.0.0:5000 --protocol=http --processes 4 --threads 2 --listen 1024 --module app:app
    app.run(debug=False) 