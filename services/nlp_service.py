import logging
import json
import re
from collections import defaultdict
from flask import current_app
from app import db
from models import Message

logger = logging.getLogger(__name__)

class NLPService:
    """Service for natural language processing to understand user intents and entities"""
    
    def __init__(self, app=None):
        self.app = app
        self.intent_patterns = self._define_intent_patterns()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        logger.info("Initialized NLP service with keyword-based extraction")
    
    def _define_intent_patterns(self):
        """Define regex patterns for intent recognition"""
        patterns = {
            "find_service": [
                r"(?i)find|locate|search|looking for|need|where (is|can I find)",
                r"(?i)nearby|closest|nearest",
                r"(?i)help (me )?(find|locate|with)"
            ],
            "get_directions": [
                r"(?i)directions?|way to|route to|path to|how (do I|to) get to",
                r"(?i)guide me to|navigate|go to"
            ],
            "service_hours": [
                r"(?i)hours|open|close|when|time",
                r"(?i)operating hours|business hours|working hours"
            ],
            "required_documents": [
                r"(?i)documents?|papers?|bring|need to have|requirements?",
                r"(?i)what (do I|should I) bring|identification|ID"
            ],
            "connect_call": [
                r"(?i)call|phone|speak|talk to|connect( me)? (with|to)",
                r"(?i)contact (details|information|number)"
            ],
            "confirm_service": [
                r"(?i)done|completed|finished|received|got (the )?service",
                r"(?i)success(ful)?|thank you|thanks"
            ],
            "deny_service": [
                r"(?i)not (done|completed|received)|didn't (get|receive)",
                r"(?i)problem|issue|failed|unsuccessful|no"
            ],
            "greeting": [
                r"(?i)hello|hi|hey|greetings|good (morning|afternoon|evening)"
            ],
            "help": [
                r"(?i)help|assist|support|how (do|can) (I|you)|what can you do"
            ]
        }
        return patterns
    
    def detect_language(self, text):
        """Detect if the text is in English or Kinyarwanda"""
        # Simple rules for language detection
        # In a real implementation, use a proper language detection library
        
        # Common Kinyarwanda words
        kinyarwanda_words = [
            'muraho', 'amakuru', 'yego', 'oya', 'murakoze', 'ndashaka', 
            'mfasha', 'kubona', 'serivisi', 'aho', 'kugera'
        ]
        
        text_lower = text.lower()
        
        # Count Kinyarwanda words in the text
        kinyarwanda_count = sum(1 for word in kinyarwanda_words if word in text_lower)
        
        # If multiple Kinyarwanda words found, assume it's Kinyarwanda
        if kinyarwanda_count >= 2:
            return 'rw'
        
        # Default to English
        return 'en'
    
    def detect_intent(self, text):
        """Detect the user's intent from the text"""
        intent_scores = defaultdict(int)
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                intent_scores[intent] += len(matches)
        
        # Get the intent with the highest score
        if intent_scores:
            top_intent = max(intent_scores.items(), key=lambda x: x[1])
            if top_intent[1] > 0:
                return top_intent[0]
        
        # Default intent if no patterns match
        return "general_inquiry"
    
    def extract_entities(self, text, language='en'):
        """Extract named entities from text using keyword-based approaches"""
        entities = {}
        text_lower = text.lower()
        words = text.split()
        
        # Extract service types using keywords
        service_keywords = {
            'health': ['hospital', 'clinic', 'health center', 'doctor', 'medical', 'healthcare'],
            'education': ['school', 'university', 'college', 'education', 'academic'],
            'identification': ['ID', 'passport', 'identification', 'identity card', 'birth certificate'],
            'taxation': ['tax', 'taxes', 'revenue', 'payment', 'financial'],
            'social': ['social security', 'welfare', 'unemployment', 'benefits', 'assistance']
        }
        
        service_types = []
        for service_type, keywords in service_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    service_types.append(service_type)
                    break
        
        if service_types:
            entities['SERVICE_TYPE'] = service_types
        
        # Simple location extraction
        location_keywords = ['in', 'at', 'near', 'around', 'by']
        for i, word in enumerate(words):
            if word.lower() in location_keywords and i < len(words) - 1:
                potential_location = words[i+1]
                if potential_location not in ['the', 'a', 'an'] and len(potential_location) > 2:
                    entities['LOC'] = [potential_location]
                    break
        
        # Person extraction - simple name detection
        person_prefixes = ['mr', 'mrs', 'ms', 'dr', 'prof']
        for i, word in enumerate(words):
            if i < len(words) - 1 and word.lower().rstrip('.') in person_prefixes:
                potential_name = words[i+1]
                if len(potential_name) > 1 and potential_name[0].isupper():
                    entities['PERSON'] = [f"{word} {potential_name}"]
                    break
        
        # Organization extraction - detect capital words followed by common org suffixes
        org_suffixes = ['ministry', 'department', 'office', 'agency', 'authority', 'center', 'commission']
        for suffix in org_suffixes:
            pattern = re.compile(r'\b([A-Z][a-z]+ )+' + suffix + r'\b', re.IGNORECASE)
            matches = pattern.findall(text)
            if matches:
                entities['ORG'] = matches
                break
        
        # Date extraction - simple pattern for dates
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # DD/MM/YYYY or MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # DD-MM-YYYY or MM-DD-YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:st|nd|rd|th)?,? \d{4}\b'  # Month DD, YYYY
        ]
        
        date_matches = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            date_matches.extend(matches)
        
        if date_matches:
            entities['DATE'] = date_matches
            
        return entities
    
    def process_message(self, message_id):
        """Process a message to extract intent and entities"""
        try:
            # Get the message from the database
            message = Message.query.get(message_id)
            if not message:
                logger.error(f"Message with ID {message_id} not found")
                return None
            
            # Detect language if not already set
            language = message.language or self.detect_language(message.content)
            
            # Detect intent
            intent = self.detect_intent(message.content)
            
            # Extract entities
            entities = self.extract_entities(message.content, language)
            
            # Update the message with NLP results
            message.intent = intent
            message.entities = json.dumps(entities)
            message.language = language
            
            db.session.commit()
            
            logger.info(f"Processed message {message_id}: intent={intent}, language={language}")
            
            return {
                'intent': intent,
                'entities': entities,
                'language': language
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing message: {e}")
            return None
    
    def get_service_type_from_entities(self, entities):
        """Extract service type from entities dictionary"""
        if not entities or 'SERVICE_TYPE' not in entities:
            return None
        
        service_types = entities['SERVICE_TYPE']
        return service_types[0] if service_types else None
    
    def get_location_from_entities(self, entities):
        """Extract location from entities dictionary"""
        location_entity_types = ['GPE', 'LOC', 'FAC']
        
        for entity_type in location_entity_types:
            if entity_type in entities and entities[entity_type]:
                return entities[entity_type][0]
        
        return None
