import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate
from celery import Celery
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy base
class Base(DeclarativeBase):
    pass

# Initialize Flask extensions
db = SQLAlchemy(model_class=Base)
migrate = Migrate()

# Initialize Celery
celery = Celery(__name__, 
                broker=Config.CELERY_BROKER_URL,
                backend=Config.CELERY_RESULT_BACKEND)

def create_app(config_class=Config):
    # Create and configure the Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = os.environ.get("SESSION_SECRET", config_class.SECRET_KEY)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure Celery
    celery.conf.update(app.config)
    
    # Register blueprints
    from routes.api import api_bp
    from routes.web import web_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)
    
    # Create database tables if they don't exist
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        import models
        
        try:
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Check if we need to import sample data
            from models import GovernmentService
            if GovernmentService.query.count() == 0:
                logger.info("No services found. Importing sample data...")
                from data.sample_services import import_sample_services
                import_sample_services()
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
    
    logger.info("Application initialized successfully")
    return app

# Initialize the Celery app
def init_celery(app=None):
    app = app or create_app()
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
