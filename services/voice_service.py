import logging
import os
import tempfile
import json
import africastalking
from flask import current_app, url_for
from app import db
from models import User, Conversation, Message

logger = logging.getLogger(__name__)

class VoiceService:
    """Service for handling voice call interactions using Africa's Talking Voice API"""
    
    def __init__(self, app=None):
        self.app = app
        self.voice = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        
        # Initialize Africa's Talking SDK
        username = app.config.get('AT_USERNAME')
        api_key = app.config.get('AT_API_KEY')
        
        try:
            africastalking.initialize(username, api_key)
            self.voice = africastalking.Voice
            logger.info("Africa's Talking Voice client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Africa's Talking Voice client: {e}")
            self.voice = None
    
    def handle_incoming_call(self, caller_number, session_id, is_active=True):
        """Process incoming voice call"""
        try:
            # Find or create user
            user = User.query.filter_by(phone_number=caller_number).first()
            if not user:
                user = User(phone_number=caller_number)
                db.session.add(user)
                db.session.flush()
                logger.info(f"Created new user with phone {caller_number}")
            
            # Create a new conversation
            conversation = Conversation(
                user_id=user.id,
                channel='voice',
                status='active' if is_active else 'completed',
                current_state='greeting',
                context={'session_id': session_id}
            )
            db.session.add(conversation)
            db.session.commit()
            
            logger.info(f"Recorded incoming call from {caller_number}")
            
            return user, conversation
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling incoming call: {e}")
            return None, None
    
    def generate_voice_response(self, action_type, **kwargs):
        """Generate XML response for voice calls"""
        if action_type == "greeting":
            # Generate a greeting message
            language = kwargs.get('language', 'en')
            
            if language == 'en':
                speech = "Welcome to Tugendane. How can I help you today? Please say what government service you are looking for."
            else:  # Kinyarwanda
                speech = "Murakaza neza kuri Tugendane. Nigute nabafasha uyu munsi? Muvuge ni service y'i guverinoma irimo mushaka."
            
            response = f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="en-US-Standard-D" playBeep="false">{speech}</Say>
                <Record 
                    finishOnKey="#" 
                    maxLength="30" 
                    trimSilence="true"
                    playBeep="true" 
                    callbackUrl="{kwargs.get('callback_url', '')}"
                />
            </Response>
            """
            return response
            
        elif action_type == "service_confirmation":
            service_name = kwargs.get('service_name', 'the requested service')
            language = kwargs.get('language', 'en')
            
            if language == 'en':
                speech = f"I found {service_name} near you. Would you like directions? Say yes or no."
            else:  # Kinyarwanda
                speech = f"Nabonye {service_name} hafi yawe. Urashaka amabwiriza? Vuga yego cyangwa oya."
            
            response = f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="en-US-Standard-D" playBeep="false">{speech}</Say>
                <GetDigits 
                    timeout="30"
                    finishOnKey="#"
                    callbackUrl="{kwargs.get('callback_url', '')}"
                >
                    <Say>Press 1 for yes, 2 for no.</Say>
                </GetDigits>
            </Response>
            """
            return response
            
        elif action_type == "directions":
            directions = kwargs.get('directions', 'No directions available.')
            language = kwargs.get('language', 'en')
            
            if language == 'en':
                intro = "Here are the directions to the service: "
            else:  # Kinyarwanda
                intro = "Dore amabwiriza yo kugera kuri service: "
            
            response = f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="en-US-Standard-D" playBeep="false">{intro}{directions}</Say>
                <Say>Thank you for using Tugendane. Goodbye!</Say>
                <Hangup/>
            </Response>
            """
            return response
            
        elif action_type == "connect_call":
            service_phone = kwargs.get('service_phone', '')
            language = kwargs.get('language', 'en')
            
            if language == 'en':
                speech = "Connecting you to the service now. Please wait."
            else:  # Kinyarwanda
                speech = "Ndimo kubahuza na service ubu. Mwihangane."
            
            response = f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="en-US-Standard-D" playBeep="false">{speech}</Say>
                <Dial phoneNumbers="{service_phone}" 
                      record="true" 
                      sequential="true"
                      callbackUrl="{kwargs.get('callback_url', '')}"
                />
            </Response>
            """
            return response
            
        elif action_type == "no_service_found":
            language = kwargs.get('language', 'en')
            
            if language == 'en':
                speech = "I'm sorry, I couldn't find any services matching your request. Please try again with a different request."
            else:  # Kinyarwanda
                speech = "Mbabarira, sinshobora kubona serivisi zijyanye n'icyo usaba. Ongera ugerageze n'icyifuzo gitandukanye."
            
            response = f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="en-US-Standard-D" playBeep="false">{speech}</Say>
                <Record 
                    finishOnKey="#" 
                    maxLength="30" 
                    trimSilence="true"
                    playBeep="true" 
                    callbackUrl="{kwargs.get('callback_url', '')}"
                />
            </Response>
            """
            return response
            
        else:
            # Default response
            response = """
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say>Thank you for calling Tugendane. Goodbye!</Say>
                <Hangup/>
            </Response>
            """
            return response
    
    def make_call(self, phone_number, callback_url):
        """Initiate an outbound call to a user"""
        if not self.voice:
            logger.error("Voice client not initialized")
            return False, "Voice client not initialized"
        
        try:
            # Make the call
            response = self.voice.call({
                'callFrom': current_app.config.get('AT_SHORTCODE', '+254711082000'),
                'callTo': [phone_number],
                'callbackUrl': callback_url
            })
            
            # Log the response
            logger.info(f"Call initiated: {response}")
            
            # Check if call was initialized successfully
            if response and 'entries' in response and len(response['entries']) > 0:
                status = response['entries'][0]['status']
                if status == 'Queued':
                    return True, response['entries'][0]
            
            return False, "Failed to initiate call"
            
        except Exception as e:
            logger.error(f"Error initiating call: {e}")
            return False, str(e)
    
    def process_speech_to_text(self, audio_url):
        """Process recorded audio to extract text (using open-source STT)"""
        # Note: In a real implementation, this would use Coqui STT or similar
        # For this prototype, we'll simulate STT with a placeholder
        logger.info(f"Processing speech to text from: {audio_url}")
        
        # Placeholder for actual STT implementation
        # This would download the audio file and pass it to the STT engine
        text = "This is a placeholder for speech-to-text conversion"
        
        return text
    
    def record_voice_message(self, conversation_id, content, is_user=True):
        """Record a voice message in the database"""
        try:
            message = Message(
                conversation_id=conversation_id,
                sender_type='user' if is_user else 'system',
                message_type='voice',
                content=content
            )
            db.session.add(message)
            db.session.commit()
            
            logger.info(f"Recorded voice message in conversation {conversation_id}")
            return message
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording voice message: {e}")
            return None
