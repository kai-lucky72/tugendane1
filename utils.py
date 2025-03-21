import re
import json
import random
import string
import logging
from datetime import datetime, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)

def generate_session_id():
    """Generate a random session ID for conversations"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(16))

def extract_keywords(text):
    """Extract important keywords from text"""
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation and extra spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split into words
    words = text.split()
    
    # Remove common stopwords
    stopwords = {
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 
        'you', 'your', 'yours', 'yourself', 'yourselves', 
        'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 
        'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 
        'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 
        'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
        'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 
        'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 
        'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 
        'against', 'between', 'into', 'through', 'during', 'before', 'after', 
        'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 
        'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 
        'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 
        'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
    }
    
    # Keep only non-stopwords
    keywords = [word for word in words if word not in stopwords and len(word) > 2]
    
    return keywords

def format_coordinates_for_postgis(latitude, longitude):
    """Format coordinates for PostGIS POINT geometry"""
    return f'POINT({longitude} {latitude})'

def is_valid_phone_number(phone):
    """Validate phone number format"""
    # Basic validation for international format
    pattern = r'^\+?[0-9]{7,15}$'
    return bool(re.match(pattern, phone))

def safe_json_loads(json_str, default=None):
    """Safely load JSON string, returning default if invalid"""
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning(f"Failed to decode JSON: {json_str}")
        return default

def format_timestamp(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """Format a timestamp for display"""
    if not timestamp:
        return ''
    
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return timestamp
    
    return timestamp.strftime(format_str)

def get_distance_text(distance_km):
    """Format distance for human-readable display"""
    if distance_km < 1:
        # Convert to meters
        meters = int(distance_km * 1000)
        return f"{meters} meters"
    else:
        return f"{distance_km:.1f} km"
