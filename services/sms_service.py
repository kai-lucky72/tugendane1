import logging
import africastalking
from flask import current_app
from app import db
from models import User, Conversation, Message

logger = logging.getLogger(__name__)

class SMSService:
    """Service for handling SMS interactions using Africa's Talking API"""
    
    def __init__(self, app=None):
        self.app = app
        self.sms = None
        
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
            self.sms = africastalking.SMS
            logger.info("Africa's Talking SMS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Africa's Talking SMS client: {e}")
            self.sms = None
    
    def send_sms(self, recipient, message):
        """Send SMS to a single recipient"""
        if not self.sms:
            logger.error("SMS client not initialized")
            return False, "SMS client not initialized"
        
        try:
            # Send the message
            response = self.sms.send(message, [recipient])
            
            # Log the response
            logger.info(f"SMS sent: {response}")
            
            # Check if message was sent successfully
            if response and 'SMSMessageData' in response and 'Recipients' in response['SMSMessageData']:
                recipients = response['SMSMessageData']['Recipients']
                if recipients and len(recipients) > 0:
                    status = recipients[0]['status']
                    if status == 'Success':
                        return True, "Message sent successfully"
            
            return False, "Failed to send message"
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False, str(e)
    
    def handle_incoming_sms(self, sender, message_text, session_id=None):
        """Process incoming SMS message"""
        try:
            # Find or create user
            user = User.query.filter_by(phone_number=sender).first()
            if not user:
                user = User(phone_number=sender)
                db.session.add(user)
                db.session.flush()
                logger.info(f"Created new user with phone {sender}")
            
            # Find active conversation or create new one
            conversation = Conversation.query.filter_by(
                user_id=user.id, 
                channel='sms', 
                status='active'
            ).order_by(Conversation.last_message_at.desc()).first()
            
            if not conversation:
                conversation = Conversation(
                    user_id=user.id,
                    channel='sms',
                    status='active',
                    current_state='initial'
                )
                db.session.add(conversation)
                db.session.flush()
                logger.info(f"Created new conversation for user {user.id}")
            
            # Create message record
            message = Message(
                conversation_id=conversation.id,
                sender_type='user',
                message_type='sms',
                content=message_text
            )
            db.session.add(message)
            
            # Update conversation last activity time
            conversation.last_message_at = db.func.now()
            db.session.commit()
            
            logger.info(f"Recorded SMS from {sender}: {message_text}")
            
            # Return the message and conversation for further processing
            return user, conversation, message
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling incoming SMS: {e}")
            return None, None, None
    
    def send_response(self, user, conversation, response_text):
        """Send response SMS and record it in the database"""
        success, message = self.send_sms(user.phone_number, response_text)
        
        if success:
            # Record the response in the database
            response_message = Message(
                conversation_id=conversation.id,
                sender_type='system',
                message_type='sms',
                content=response_text
            )
            db.session.add(response_message)
            
            # Update conversation last activity time
            conversation.last_message_at = db.func.now()
            db.session.commit()
            
            logger.info(f"Response SMS sent to {user.phone_number} and recorded")
            return True
        else:
            logger.error(f"Failed to send response SMS: {message}")
            return False
