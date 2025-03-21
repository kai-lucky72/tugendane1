import logging
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, flash, session
from app import db
from models import User, Conversation, Message, GovernmentService, UserInteraction
from services.nlp_service import NLPService
from services.geo_service import GeoService
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)

# Create blueprint
web_bp = Blueprint('web', __name__)

# Initialize services
nlp_service = NLPService()
geo_service = GeoService()

@web_bp.before_request
def initialize_services():
    """Initialize services with the current Flask app"""
    if not nlp_service.app:
        nlp_service.init_app(current_app)
    if not geo_service.app:
        geo_service.init_app(current_app)

@web_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@web_bp.route('/chat')
def chat():
    """Web-based chat interface"""
    return render_template('chat.html')

@web_bp.route('/chat/send', methods=['POST'])
def send_chat_message():
    """Handle incoming chat message from web interface"""
    try:
        # Get message data
        message_text = request.form.get('message')
        user_id = request.form.get('user_id')
        
        if not message_text:
            return jsonify({'status': 'error', 'message': 'No message provided'}), 400
        
        # Get or create user (for demo purposes, use a default user)
        if not user_id or user_id == 'new':
            # Create a demo web user
            web_phone = f"web-{func.random()}"
            user = User(phone_number=web_phone, language_preference='en')
            db.session.add(user)
            db.session.flush()
            user_id = user.id
        else:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get or create conversation
        conversation = Conversation.query.filter_by(
            user_id=user.id,
            channel='web',
            status='active'
        ).order_by(Conversation.last_message_at.desc()).first()
        
        if not conversation:
            conversation = Conversation(
                user_id=user.id,
                channel='web',
                status='active',
                current_state='initial'
            )
            db.session.add(conversation)
            db.session.flush()
        
        # Create message
        message = Message(
            conversation_id=conversation.id,
            sender_type='user',
            message_type='web',
            content=message_text
        )
        db.session.add(message)
        
        # Update conversation timestamp
        conversation.last_message_at = db.func.now()
        db.session.commit()
        
        # Process the message with NLP
        nlp_result = nlp_service.process_message(message.id)
        
        # Generate response based on intent
        if nlp_result:
            intent = nlp_result['intent']
            entities = nlp_result['entities']
            
            # Simple demo response based on intent
            if intent == 'greeting':
                response = "Hello! I can help you find nearby government services in Rwanda. What are you looking for today?"
            elif intent == 'find_service':
                service_type = nlp_service.get_service_type_from_entities(entities)
                response = f"I can help you find {service_type or 'government'} services. Please provide your location in Rwanda."
            elif intent == 'get_directions':
                response = "I can provide directions to government services. Please specify what service you need and your location."
            elif intent == 'help':
                response = "I can help you find government services, provide directions, check operating hours, and more. Just let me know what you need."
            else:
                response = "I understand you're looking for government services. Could you provide more details about what you need and your location?"
        else:
            response = "I'm here to help you find government services in Rwanda. How can I assist you today?"
        
        # Record system response
        system_message = Message(
            conversation_id=conversation.id,
            sender_type='system',
            message_type='web',
            content=response
        )
        db.session.add(system_message)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'user_id': user.id,
            'response': response
        })
        
    except Exception as e:
        logger.error(f"Error in send_chat_message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@web_bp.route('/webhooks')
def show_webhooks():
    """Display webhook URLs for configuration"""
    return jsonify({
        'sms_webhook_url': current_app.config['SMS_WEBHOOK_URL'],
        'voice_webhook_url': current_app.config['VOICE_WEBHOOK_URL']
    })

@web_bp.route('/services')
def services_map():
    """Map view of government services"""
    return render_template('services_map.html')

@web_bp.route('/api/services')
def get_services():
    """API endpoint to get all services for map"""
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=10, type=float)  # 10km default radius
        
        if not lat or not lng:
            # Default to Rwanda center
            lat = -1.9403
            lng = 29.8739
        
        if lat and lng:
            # Get services near the user's location
            services = GovernmentService.query.order_by(
                GovernmentService.location.distance_centroid(
                    'POINT({} {})'.format(lng, lat)
                )
            ).limit(10).all()
        else:
            # Get all services if no location provided
            services = GovernmentService.query.all()
        
        # Format services for map display
        service_list = []
        for service in services:
            service_list.append({
                'id': service.id,
                'name': service.name,
                'category': service.category,
                'address': service.address,
                'latitude': service.latitude,
                'longitude': service.longitude,
                'phone_number': service.phone_number,
                'opening_hours': service.opening_hours
            })
        
        return jsonify({'services': service_list})
        
    except Exception as e:
        logger.error(f"Error getting services: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@web_bp.route('/admin')
def admin():
    """Admin dashboard for monitoring"""
    # Get statistics
    user_count = User.query.count()
    conversation_count = Conversation.query.count()
    service_count = GovernmentService.query.count()
    interaction_count = UserInteraction.query.count()
    
    # Get recent conversations
    recent_conversations = db.session.query(
        Conversation, User
    ).join(
        User, User.id == Conversation.user_id
    ).order_by(
        Conversation.last_message_at.desc()
    ).limit(10).all()
    
    # Get service usage statistics
    service_usage = db.session.query(
        GovernmentService.name,
        GovernmentService.category,
        func.count(UserInteraction.id).label('usage_count')
    ).join(
        UserInteraction, UserInteraction.service_id == GovernmentService.id
    ).group_by(
        GovernmentService.id
    ).order_by(
        desc('usage_count')
    ).limit(10).all()
    
    return render_template(
        'admin.html',
        user_count=user_count,
        conversation_count=conversation_count,
        service_count=service_count,
        interaction_count=interaction_count,
        recent_conversations=recent_conversations,
        service_usage=service_usage
    )

@web_bp.route('/admin/conversation/<int:conversation_id>')
def view_conversation(conversation_id):
    """View details of a conversation"""
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
    user = User.query.get(conversation.user_id)
    
    return render_template(
        'conversation_detail.html',
        conversation=conversation,
        messages=messages,
        user=user
    )
