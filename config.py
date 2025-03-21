import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-tugendane')

    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tugendane.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
    }

    # Africa's Talking API configuration for Rwanda
    AT_USERNAME = os.environ.get('AT_USERNAME', 'sandbox')
    AT_API_KEY = os.environ.get('AT_API_KEY', 'your_api-key')
    AT_SHORTCODE = os.environ.get('AT_SHORTCODE', '12345')
    AT_SENDER_ID = os.environ.get('AT_SENDER_ID', 'TUGENDANE')  # For alphanumeric sender ID
    AT_COUNTRY_CODE = '+250'  # Rwanda country code

    # OpenAI configuration for LLM
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your-openai-key')

    # Celery configuration
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)

    # Service configuration
    DEBUG = True
    PORT = 5000
    HOST = '0.0.0.0'