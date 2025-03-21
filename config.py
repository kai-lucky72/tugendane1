import os

class Config:
    """Application configuration settings"""
    # Flask configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'tugendane-dev-key')
    DEBUG = True
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Africa's Talking API keys
    AT_USERNAME = os.environ.get('AT_USERNAME', 'sandbox')
    AT_API_KEY = os.environ.get('AT_API_KEY', 'your_api_key')
    AT_SHORTCODE = os.environ.get('AT_SHORTCODE', '12345')
    
    # Voice API settings
    VOICE_API_KEY = os.environ.get('VOICE_API_KEY')
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # GraphHopper routing API
    GRAPHHOPPER_API_KEY = os.environ.get('GRAPHHOPPER_API_KEY', 'your_api_key')
    
    # NLP configurations
    SUPPORTED_LANGUAGES = ['en', 'rw']  # English and Kinyarwanda
    DEFAULT_LANGUAGE = 'en'

    # Application settings
    SERVICE_SEARCH_RADIUS_KM = 10  # Default search radius for services in kilometers
    FOLLOW_UP_DELAY_HOURS = 24  # Hours to wait before sending follow-up SMS
