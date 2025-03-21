import logging
import spacy
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
        self.nlp_models = {}
        self.intent_patterns = self._define_intent_patterns()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        
        # Load spaCy models for supported languages
        try:
            # Load English model
            self.nlp_models['en'] = spacy.load('en_core_web_sm')
            logger.info("Loaded English NLP model")
            
            # We'd load Kinyarwanda model here if available
            # For prototype, we'll use English model for all languages
            self.nlp_models['rw'] = self.nlp_models['en']
            logger.info("Using English model for Kinyarwanda (placeholder)")
            
        except Exception as e:
            logger.error(f"Error loading NLP models: {e}")
    
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
        """Extract named entities from text"""
        if language not in self.nlp_models:
            language = 'en'  # Fallback to English
        
        nlp = self.nlp_models[language]
        doc = nlp(text)
        
        entities = {}
        
        # Extract entities from spaCy
        for ent in doc.ents:
            entity_type = ent.label_
            entity_value = ent.text
            
            if entity_type not in entities:
                entities[entity_type] = []
                
            entities[entity_type].append(entity_value)
        
        # Extract service types using keywords
        service_keywords = {
            'health': ['hospital', 'clinic', 'health center', 'doctor', 'medical', 'healthcare'],
            'education': ['school', 'university', 'college', 'education', 'academic'],
            'identification': ['ID', 'passport', 'identification', 'identity card', 'birth certificate'],
            'taxation': ['tax', 'taxes', 'revenue', 'payment', 'financial'],
            'social': ['social security', 'welfare', 'unemployment', 'benefits', 'assistance']
        }
        
        service_types = []
        text_lower = text.lower()
        
        for service_type, keywords in service_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    service_types.append(service_type)
                    break
        
        if service_types:
            entities['SERVICE_TYPE'] = service_types
        
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
