from flask import Flask, render_template, redirect, url_for, flash
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os

from extensions import db, mail, csrf
from config import config
from utils import init_app_data
from routes.auth import auth_bp
from routes.main import main_bp
from routes.queries import queries_bp
from routes.responses import responses_bp
from routes.comments import comments_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
        'pool_pre_ping': True,
        'pool_recycle': 300
    }

    import logging
    from logging.handlers import RotatingFileHandler
    
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/kable.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Kable startup')

    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # Inicjalizacja Flask-Login
    from flask_login import LoginManager
    from models import User
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(queries_bp)
    app.register_blueprint(responses_bp)
    app.register_blueprint(comments_bp)
    
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    return app

app = create_app()

@app.context_processor
def utility_processor():
    def format_datetime(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(ZoneInfo("Europe/Warsaw"))
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')

    return {
        'format_datetime': format_datetime, 
        'datetime': datetime
    }

@app.errorhandler(401)
def unauthorized(error):
    flash('Musisz się zalogować, aby uzyskać dostęp do tej strony.', 'warning')
    return redirect(url_for('auth.login'))

# Inicjalizacja danych przy starcie
with app.app_context():
    init_app_data()
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)