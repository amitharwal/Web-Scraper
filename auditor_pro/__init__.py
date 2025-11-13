"""
Application factory for Page Auditor Pro.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from .config import config
from datetime import datetime
from celery import Celery
from flask_mail import Mail
from flask_socketio import SocketIO

celery = Celery(
    __name__,
    broker=config['default'].CELERY_BROKER_URL,
    include=['auditor_pro.tasks']
)

# Initialize other extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
mail = Mail()
login_manager = LoginManager()
socketio = SocketIO()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_name='default'):
    """
    Application Factory.
    """
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='static')

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions with the app
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Initialize SocketIO with Redis as the message queue
    socketio.init_app(app, message_queue=app.config['CELERY_BROKER_URL'])

    # Update the Celery config from the loaded app config
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    app.celery_app = celery

    # --- Register Blueprints ---
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    # --- Register Context Processors ---
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    # --- Database Creation ---
    with app.app_context():
        db.create_all()

    return app