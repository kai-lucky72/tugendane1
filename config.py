import os
import sqlite3
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-tugendane')

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///instance/tugendane.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        'echo': True,
    }
    # Enable SQLite extensions for spatial support
    SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {'detect_types': sqlite3.PARSE_DECLTYPES}
    SQLALCHEMY_ENGINE_OPTIONS['creator'] = lambda: sqlite3.connect('instance/tugendane.db', uri=True)


    # Africa's Talking API configuration for Rwanda
    AT_USERNAME = os.environ.get('AT_USERNAME', 'sandbox')
    AT_API_KEY = os.environ.get('AT_API_KEY')
    AT_SHORTCODE = os.environ.get('AT_SHORTCODE', '12345')
    AT_SENDER_ID = os.environ.get('AT_SENDER_ID', 'TUGENDANE')  # For alphanumeric sender ID
    AT_COUNTRY_CODE = '+250'  # Rwanda country code

    # Webhook configuration
    BASE_URL = os.environ.get('BASE_URL', f'https://{os.environ.get("REPL_SLUG")}.{os.environ.get("REPL_OWNER")}.repl.co')
    SMS_WEBHOOK_PATH = '/api/sms/receive'
    VOICE_WEBHOOK_PATH = '/api/voice/receive'

    # Full webhook URLs
    SMS_WEBHOOK_URL = f'{BASE_URL}{SMS_WEBHOOK_PATH}'
    VOICE_WEBHOOK_URL = f'{BASE_URL}{VOICE_WEBHOOK_PATH}'

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