import logging
from datetime import datetime, timedelta
from celery import shared_task
from app import db, create_app
from models import UserInteraction, User, Conversation, Message
from services.sms_service import SMSService

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for scheduling follow-up messages and tasks"""
    
    def __init__(self, app=None):
        self.app = app
        self.sms_service = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        self.sms_service = SMSService(app)
    
    def schedule_follow_up(self, interaction_id, delay_hours=24):
        """Schedule a follow-up SMS for a user interaction"""
        try:
            # Get the interaction
            interaction = UserInteraction.query.get(interaction_id)
            if not interaction:
                logger.error(f"Interaction with ID {interaction_id} not found")
                return False
            
            # Mark the interaction for follow-up
            interaction.follow_up_scheduled = True
            db.session.commit()
            
            # Schedule the Celery task
            send_follow_up_task.apply_async(
                args=[interaction_id],
                countdown=delay_hours * 3600  # Convert hours to seconds
            )
            
            logger.info(f"Scheduled follow-up for interaction {interaction_id} in {delay_hours} hours")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error scheduling follow-up: {e}")
            return False
    
    def process_follow_up_response(self, user_id, message_text):
        """Process a user's response to a follow-up message"""
        try:
            # Find the most recent interaction with follow-up sent
            interaction = UserInteraction.query.filter_by(
                user_id=user_id,
                follow_up_sent=True,
                follow_up_response=None
            ).order_by(UserInteraction.follow_up_sent_at.desc()).first()
            
            if not interaction:
                logger.warning(f"No pending follow-up found for user {user_id}")
                return False
            
            # Record the user's response
            interaction.follow_up_response = message_text
            interaction.follow_up_response_at = datetime.utcnow()
            
            # Update the interaction status based on the response
            lowercase_text = message_text.lower()
            if any(word in lowercase_text for word in ['yes', 'yego', 'completed', 'done', 'received']):
                interaction.status = 'completed'
            else:
                interaction.status = 'issue_reported'
            
            db.session.commit()
            
            logger.info(f"Processed follow-up response for interaction {interaction.id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing follow-up response: {e}")
            return False

@shared_task
def send_follow_up_task(interaction_id):
    """Celery task to send a follow-up SMS"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the interaction
            interaction = UserInteraction.query.get(interaction_id)
            if not interaction:
                logger.error(f"Interaction with ID {interaction_id} not found")
                return False
            
            # Get the user
            user = User.query.get(interaction.user_id)
            if not user:
                logger.error(f"User with ID {interaction.user_id} not found")
                return False
            
            # Get the service
            service = interaction.service
            
            # Determine language
            language = user.language_preference or 'en'
            
            # Create SMS message based on language
            if language == 'en':
                message = f"Hello from Tugendane! Did you receive the service you were looking for at {service.name}? Please reply with YES or NO."
            else:  # Kinyarwanda
                message = f"Mwaramutse Tugendane! Wabonye service wari gushaka kuri {service.name}? Subiza YEGO cyangwa OYA."
            
            # Initialize SMS service
            sms_service = SMSService(app)
            
            # Send the follow-up SMS
            success, response = sms_service.send_sms(user.phone_number, message)
            
            if success:
                # Update the interaction
                interaction.follow_up_sent = True
                interaction.follow_up_sent_at = datetime.utcnow()
                
                # Create a new conversation for the follow-up if needed
                conversation = Conversation.query.filter_by(
                    user_id=user.id,
                    status='active'
                ).order_by(Conversation.last_message_at.desc()).first()
                
                if not conversation:
                    conversation = Conversation(
                        user_id=user.id,
                        channel='sms',
                        status='active',
                        current_state='follow_up'
                    )
                    db.session.add(conversation)
                    db.session.flush()
                
                # Record the message
                message_record = Message(
                    conversation_id=conversation.id,
                    sender_type='system',
                    message_type='sms',
                    content=message
                )
                db.session.add(message_record)
                db.session.commit()
                
                logger.info(f"Sent follow-up SMS for interaction {interaction_id}")
                return True
            else:
                logger.error(f"Failed to send follow-up SMS: {response}")
                return False
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in send_follow_up_task: {e}")
            return False
