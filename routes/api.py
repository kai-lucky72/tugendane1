import logging
import json
from flask import Blueprint, request, jsonify, current_app, url_for
from app import db
from models import User, Conversation, Message, GovernmentService, UserInteraction
from services.sms_service import SMSService
from services.voice_service import VoiceService
from services.nlp_service import NLPService
from services.geo_service import GeoService
from services.scheduler import SchedulerService

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize services
sms_service = SMSService()
voice_service = VoiceService()
nlp_service = NLPService()
geo_service = GeoService()
scheduler_service = SchedulerService()

@api_bp.before_request
def initialize_services():
    """Initialize services with the current Flask app"""
    if not sms_service.app:
        sms_service.init_app(current_app)
    if not voice_service.app:
        voice_service.init_app(current_app)
    if not nlp_service.app:
        nlp_service.init_app(current_app)
    if not geo_service.app:
        geo_service.init_app(current_app)
    if not scheduler_service.app:
        scheduler_service.init_app(current_app)

@api_bp.route('/sms/receive', methods=['POST'])
def receive_sms():
    """Endpoint for receiving SMS messages from Africa's Talking API"""
    try:
        # Get SMS data from the request
        sender = request.form.get('from')
        message = request.form.get('text')
        
        if not sender or not message:
            logger.error("Missing required SMS parameters")
            return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400
        
        # Process the incoming SMS
        user, conversation, msg = sms_service.handle_incoming_sms(sender, message)
        
        if not user or not conversation or not msg:
            logger.error("Failed to process incoming SMS")
            return jsonify({'status': 'error', 'message': 'Processing failed'}), 500
        
        # Process the message with NLP to extract intent and entities
        nlp_result = nlp_service.process_message(msg.id)
        
        # Generate and send response based on the intent
        response = process_user_intent(user, conversation, msg, nlp_result)
        
        return jsonify({'status': 'success', 'message': 'SMS processed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error in receive_sms: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/voice/receive', methods=['POST'])
def receive_call():
    """Endpoint for receiving voice calls from Africa's Talking API"""
    try:
        # Get call data from the request
        caller = request.form.get('callerNumber')
        session_id = request.form.get('sessionId')
        is_active = request.form.get('isActive') == '1'
        
        if not caller or not session_id:
            logger.error("Missing required call parameters")
            return voice_service.generate_voice_response("error")
        
        # Process the incoming call
        user, conversation = voice_service.handle_incoming_call(caller, session_id, is_active)
        
        if not user or not conversation:
            logger.error("Failed to process incoming call")
            return voice_service.generate_voice_response("error")
        
        # Generate response based on call state
        if is_active and conversation.current_state == 'greeting':
            callback_url = url_for('api.voice_recording', _external=True)
            response = voice_service.generate_voice_response(
                "greeting", 
                language=user.language_preference,
                callback_url=callback_url
            )
        else:
            response = voice_service.generate_voice_response("error")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in receive_call: {e}")
        return voice_service.generate_voice_response("error")

@api_bp.route('/voice/recording', methods=['POST'])
def voice_recording():
    """Endpoint for processing voice recordings from Africa's Talking API"""
    try:
        # Get recording data from the request
        caller = request.form.get('callerNumber')
        session_id = request.form.get('sessionId')
        recording_url = request.form.get('recordingUrl')
        
        if not caller or not session_id or not recording_url:
            logger.error("Missing required recording parameters")
            return voice_service.generate_voice_response("error")
        
        # Find the conversation
        user = User.query.filter_by(phone_number=caller).first()
        conversation = Conversation.query.filter_by(
            user_id=user.id, 
            channel='voice',
            status='active'
        ).order_by(Conversation.last_message_at.desc()).first()
        
        if not user or not conversation:
            logger.error("User or conversation not found for voice recording")
            return voice_service.generate_voice_response("error")
        
        # Process the voice recording (convert speech to text)
        text = voice_service.process_speech_to_text(recording_url)
        
        # Record the message
        msg = voice_service.record_voice_message(conversation.id, text)
        
        # Process with NLP
        nlp_result = nlp_service.process_message(msg.id)
        
        # Check for service request
        if nlp_result and nlp_result['intent'] == 'find_service':
            # Extract service type from entities
            service_type = nlp_service.get_service_type_from_entities(nlp_result['entities'])
            
            # If we have user's location, find nearby services
            if user.last_latitude and user.last_longitude:
                services = geo_service.find_nearest_services(
                    user.last_latitude, 
                    user.last_longitude,
                    service_category=service_type,
                    limit=1
                )
                
                if services:
                    service = services[0]
                    
                    # Update conversation state
                    conversation.current_state = 'service_confirmation'
                    conversation.context = json.dumps({
                        'service_id': service['id'],
                        'service_name': service['name']
                    })
                    db.session.commit()
                    
                    # Generate confirmation response
                    callback_url = url_for('api.voice_confirmation', _external=True)
                    return voice_service.generate_voice_response(
                        "service_confirmation",
                        service_name=service['name'],
                        language=user.language_preference,
                        callback_url=callback_url
                    )
                else:
                    return voice_service.generate_voice_response(
                        "no_service_found",
                        language=user.language_preference,
                        callback_url=url_for('api.voice_recording', _external=True)
                    )
            else:
                # We need location information
                # For a real implementation, we would ask for location here
                # For this prototype, we'll just return an error
                return voice_service.generate_voice_response("error")
        else:
            # Default response for unrecognized intent
            return voice_service.generate_voice_response("error")
        
    except Exception as e:
        logger.error(f"Error in voice_recording: {e}")
        return voice_service.generate_voice_response("error")

@api_bp.route('/voice/confirmation', methods=['POST'])
def voice_confirmation():
    """Endpoint for processing user confirmation from voice call"""
    try:
        # Get confirmation data from the request
        caller = request.form.get('callerNumber')
        session_id = request.form.get('sessionId')
        digits = request.form.get('dtmfDigits')
        
        if not caller or not session_id:
            logger.error("Missing required confirmation parameters")
            return voice_service.generate_voice_response("error")
        
        # Find the conversation
        user = User.query.filter_by(phone_number=caller).first()
        conversation = Conversation.query.filter_by(
            user_id=user.id, 
            channel='voice',
            status='active'
        ).order_by(Conversation.last_message_at.desc()).first()
        
        if not user or not conversation or conversation.current_state != 'service_confirmation':
            logger.error("Invalid conversation state for confirmation")
            return voice_service.generate_voice_response("error")
        
        # Get service from conversation context
        context = json.loads(conversation.context) if conversation.context else {}
        service_id = context.get('service_id')
        
        if not service_id:
            logger.error("Service ID not found in conversation context")
            return voice_service.generate_voice_response("error")
        
        # Get the service
        service = GovernmentService.query.get(service_id)
        
        if not service:
            logger.error(f"Service with ID {service_id} not found")
            return voice_service.generate_voice_response("error")
        
        # Process the user's confirmation
        if digits == '1':  # User wants directions
            # Generate directions
            directions = geo_service.get_directions(
                user.last_latitude, 
                user.last_longitude,
                service.latitude,
                service.longitude,
                language=user.language_preference
            )
            
            # Format directions as text
            directions_text = geo_service.format_directions_text(
                directions,
                language=user.language_preference
            )
            
            # Create an interaction record
            interaction = UserInteraction(
                user_id=user.id,
                service_id=service.id,
                interaction_type='direction_request',
                status='completed'
            )
            db.session.add(interaction)
            db.session.commit()
            
            # Schedule a follow-up
            scheduler_service.schedule_follow_up(interaction.id)
            
            # Return directions response
            return voice_service.generate_voice_response(
                "directions",
                directions=directions_text,
                language=user.language_preference
            )
            
        elif digits == '2':  # User wants to call the service
            if service.phone_number:
                # Create an interaction record
                interaction = UserInteraction(
                    user_id=user.id,
                    service_id=service.id,
                    interaction_type='call_connection',
                    status='in_progress'
                )
                db.session.add(interaction)
                db.session.commit()
                
                # Schedule a follow-up
                scheduler_service.schedule_follow_up(interaction.id)
                
                # Connect the call
                return voice_service.generate_voice_response(
                    "connect_call",
                    service_phone=service.phone_number,
                    language=user.language_preference,
                    callback_url=url_for('api.voice_call_status', _external=True)
                )
            else:
                # Service doesn't have a phone number
                return voice_service.generate_voice_response("error")
        else:
            # Invalid response
            return voice_service.generate_voice_response("error")
        
    except Exception as e:
        logger.error(f"Error in voice_confirmation: {e}")
        return voice_service.generate_voice_response("error")

@api_bp.route('/voice/call_status', methods=['POST'])
def voice_call_status():
    """Endpoint for tracking call connection status"""
    try:
        # Get call status data
        caller = request.form.get('callerNumber')
        session_id = request.form.get('sessionId')
        status = request.form.get('status')
        duration = request.form.get('durationInSeconds')
        
        logger.info(f"Call status: {status}, duration: {duration}s")
        
        # For this prototype, we'll just log the information
        return "", 200
        
    except Exception as e:
        logger.error(f"Error in voice_call_status: {e}")
        return "", 500

def process_user_intent(user, conversation, message, nlp_result):
    """Process user intent and generate appropriate response"""
    if not nlp_result:
        return send_default_response(user, conversation)
    
    intent = nlp_result['intent']
    entities = nlp_result['entities']
    language = nlp_result['language']
    
    # Update user's language preference if needed
    if language and user.language_preference != language:
        user.language_preference = language
        db.session.commit()
    
    # Handle different intents
    if intent == 'greeting':
        return send_greeting_response(user, conversation)
        
    elif intent == 'find_service':
        return find_service_for_user(user, conversation, entities)
        
    elif intent == 'get_directions':
        return get_directions_for_user(user, conversation, entities)
        
    elif intent == 'service_hours' or intent == 'required_documents':
        return get_service_info(user, conversation, intent, entities)
        
    elif intent == 'connect_call':
        return connect_call_to_service(user, conversation, entities)
        
    elif intent == 'confirm_service' or intent == 'deny_service':
        return process_follow_up_reply(user, conversation, intent, message.content)
        
    elif intent == 'help':
        return send_help_information(user, conversation)
        
    else:
        return send_default_response(user, conversation)

def send_greeting_response(user, conversation):
    """Send a greeting response to the user"""
    if user.language_preference == 'rw':
        message = "Muraho! Ndagufasha gushaka serivisi za guverinoma hafi yawe. Sobanura icyo ukeneye (urugero: 'ndashaka ivuriro')."
    else:  # Default to English
        message = "Hello! I can help you find nearby government services. Please describe what you need (example: 'I need a health clinic')."
    
    sms_service.send_response(user, conversation, message)
    return True

def find_service_for_user(user, conversation, entities):
    """Find a service based on user request"""
    # Extract service type from entities
    service_type = nlp_service.get_service_type_from_entities(entities)
    
    # Check if we have location information
    if user.last_latitude and user.last_longitude:
        # Find nearby services
        services = geo_service.find_nearest_services(
            user.last_latitude, 
            user.last_longitude,
            service_category=service_type
        )
        
        if services:
            # Format service information
            if user.language_preference == 'rw':
                message = f"Nabonye {len(services)} serivisi za {service_type or 'guverinoma'} hafi yawe:\n\n"
            else:
                message = f"Found {len(services)} {service_type or 'government'} services near you:\n\n"
            
            for i, service in enumerate(services[:3], 1):
                if user.language_preference == 'rw':
                    message += f"{i}. {service['name']} ({service['distance_km']} km)\n"
                    message += f"   Aho Iherereye: {service['address']}\n"
                    if service['opening_hours']:
                        message += f"   Amasaha: {service['opening_hours']}\n"
                    if service['phone_number']:
                        message += f"   Telefone: {service['phone_number']}\n"
                else:
                    message += f"{i}. {service['name']} ({service['distance_km']} km)\n"
                    message += f"   Address: {service['address']}\n"
                    if service['opening_hours']:
                        message += f"   Hours: {service['opening_hours']}\n"
                    if service['phone_number']:
                        message += f"   Phone: {service['phone_number']}\n"
                message += "\n"
            
            if user.language_preference == 'rw':
                message += "Shyiramo nomero ya service ukeneye amabwiriza yo kuyigeraho (urugero: '1')."
            else:
                message += "Enter the number of the service you want directions to (example: '1')."
            
            # Update conversation state
            conversation.current_state = 'service_selection'
            conversation.context = json.dumps({
                'service_ids': [s['id'] for s in services[:3]]
            })
            db.session.commit()
            
        else:
            # No services found
            if user.language_preference == 'rw':
                message = "Ntinabonereza service ijyanye nicyo ushaka. Gerageza ubundi."
            else:
                message = "I couldn't find any services matching your request. Please try again."
    else:
        # We need location information
        if user.language_preference == 'rw':
            message = "Kugirango nkubone serivisi, nahitaji kumenya aho uherereye. Nyamuneka, tanga izina ry'aho uherereye (urugero: 'Kigali')."
        else:
            message = "To find services, I need to know your location. Please provide a location name (example: 'Kigali')."
        
        # Update conversation state
        conversation.current_state = 'awaiting_location'
        db.session.commit()
    
    # Send the response
    sms_service.send_response(user, conversation, message)
    return True

def get_directions_for_user(user, conversation, entities):
    """Get directions to a service"""
    # Check if we're in a state where we have a selected service
    context = json.loads(conversation.context) if conversation.context else {}
    
    if conversation.current_state == 'service_selection' and 'service_ids' in context:
        # User should have sent a selection number
        # We'll handle this in the main SMS processing flow
        if user.language_preference == 'rw':
            message = "Nyamuneka, hitamo service uhitamo nomero (1, 2, ...). Shyiramo gusa nimero."
        else:
            message = "Please select a service by number (1, 2, ...). Enter just the number."
    
    else:
        # Try to extract service type and location
        service_type = nlp_service.get_service_type_from_entities(entities)
        location = nlp_service.get_location_from_entities(entities)
        
        if not service_type:
            if user.language_preference == 'rw':
                message = "Ntimvuze neza ubuhe bwoko bwa serivisi ushaka. Gerageza urugero: 'Amabwiriza yo kujya ku bitaro bya Kigali'."
            else:
                message = "I didn't understand what type of service you need. Try something like: 'Directions to the Kigali hospital'."
        elif not location and not (user.last_latitude and user.last_longitude):
            if user.language_preference == 'rw':
                message = "Nahitaji kumenya aho uherereye. Tanga izina ry'aho uherereye (urugero: 'Kigali')."
            else:
                message = "I need to know your location. Please provide a location name (example: 'Kigali')."
            
            # Update conversation state
            conversation.current_state = 'awaiting_location'
            conversation.context = json.dumps({'pending_action': 'get_directions', 'service_type': service_type})
            db.session.commit()
        else:
            # We have enough information to find services
            if not user.last_latitude and location:
                # Geocode the location
                geo_result = geo_service.geocode_location(location)
                
                if geo_result:
                    # Update user's location
                    user.last_latitude = geo_result['latitude']
                    user.last_longitude = geo_result['longitude']
                    user.last_location_timestamp = db.func.now()
                    db.session.commit()
                else:
                    if user.language_preference == 'rw':
                        message = f"Sinabashije kubona aho {location} iherereye. Gerageza indi."
                    else:
                        message = f"I couldn't find the location {location}. Please try another."
                    sms_service.send_response(user, conversation, message)
                    return True
            
            # Find nearby services
            services = geo_service.find_nearest_services(
                user.last_latitude, 
                user.last_longitude,
                service_category=service_type,
                limit=1
            )
            
            if services:
                service = services[0]
                
                # Get directions
                directions = geo_service.get_directions(
                    user.last_latitude, 
                    user.last_longitude,
                    service['latitude'],
                    service['longitude'],
                    language=user.language_preference
                )
                
                # Format directions as text
                directions_text = geo_service.format_directions_text(
                    directions,
                    language=user.language_preference
                )
                
                if user.language_preference == 'rw':
                    message = f"Amabwiriza yo kugera kuri {service['name']} ({service['distance_km']} km):\n\n"
                else:
                    message = f"Directions to {service['name']} ({service['distance_km']} km):\n\n"
                
                message += directions_text
                
                # Create an interaction record
                interaction = UserInteraction(
                    user_id=user.id,
                    service_id=service['id'],
                    interaction_type='direction_request',
                    status='completed'
                )
                db.session.add(interaction)
                db.session.commit()
                
                # Schedule a follow-up
                scheduler_service.schedule_follow_up(interaction.id)
            else:
                if user.language_preference == 'rw':
                    message = f"Sinabonye {service_type or 'serivisi'} hafi yawe. Gerageza indi."
                else:
                    message = f"I couldn't find any {service_type or 'services'} near you. Please try again."
    
    # Send the response
    sms_service.send_response(user, conversation, message)
    return True

def get_service_info(user, conversation, intent, entities):
    """Get information about a service (hours, documents, etc.)"""
    # Extract service type
    service_type = nlp_service.get_service_type_from_entities(entities)
    
    # Check if we have a selected service from context
    context = json.loads(conversation.context) if conversation.context else {}
    selected_service_id = context.get('selected_service_id')
    
    if selected_service_id:
        # Get the selected service
        service = GovernmentService.query.get(selected_service_id)
        
        if service:
            if intent == 'service_hours':
                if service.opening_hours:
                    if user.language_preference == 'rw':
                        message = f"Amasaha ya {service.name}:\n{service.opening_hours}"
                    else:
                        message = f"Opening hours for {service.name}:\n{service.opening_hours}"
                else:
                    if user.language_preference == 'rw':
                        message = f"Mbabarira, ntamakuru afite kuri amasaha ya {service.name}."
                    else:
                        message = f"Sorry, no information available about opening hours for {service.name}."
            
            elif intent == 'required_documents':
                if service.required_documents:
                    if user.language_preference == 'rw':
                        message = f"Impapuro zisabwa kuri {service.name}:\n{service.required_documents}"
                    else:
                        message = f"Required documents for {service.name}:\n{service.required_documents}"
                else:
                    if user.language_preference == 'rw':
                        message = f"Mbabarira, ntamakuru afite ku mpapuro zisabwa kuri {service.name}."
                    else:
                        message = f"Sorry, no information available about required documents for {service.name}."
            
            # Create an interaction record
            interaction = UserInteraction(
                user_id=user.id,
                service_id=service.id,
                interaction_type='information_request',
                status='completed'
            )
            db.session.add(interaction)
            db.session.commit()
        else:
            if user.language_preference == 'rw':
                message = "Mbabarira, sinabashije kubona amakuru kuri serivisi wasabye."
            else:
                message = "Sorry, I couldn't find information about the requested service."
    
    elif user.last_latitude and user.last_longitude and service_type:
        # No selected service, but we have location and service type
        # Find nearest service of that type
        services = geo_service.find_nearest_services(
            user.last_latitude, 
            user.last_longitude,
            service_category=service_type,
            limit=1
        )
        
        if services:
            service = GovernmentService.query.get(services[0]['id'])
            
            if service:
                if intent == 'service_hours':
                    if service.opening_hours:
                        if user.language_preference == 'rw':
                            message = f"Amasaha ya {service.name} ({services[0]['distance_km']} km kuva aho uri):\n{service.opening_hours}"
                        else:
                            message = f"Opening hours for {service.name} ({services[0]['distance_km']} km away):\n{service.opening_hours}"
                    else:
                        if user.language_preference == 'rw':
                            message = f"Mbabarira, ntamakuru afite kuri amasaha ya {service.name}."
                        else:
                            message = f"Sorry, no information available about opening hours for {service.name}."
                
                elif intent == 'required_documents':
                    if service.required_documents:
                        if user.language_preference == 'rw':
                            message = f"Impapuro zisabwa kuri {service.name} ({services[0]['distance_km']} km kuva aho uri):\n{service.required_documents}"
                        else:
                            message = f"Required documents for {service.name} ({services[0]['distance_km']} km away):\n{service.required_documents}"
                    else:
                        if user.language_preference == 'rw':
                            message = f"Mbabarira, ntamakuru afite ku mpapuro zisabwa kuri {service.name}."
                        else:
                            message = f"Sorry, no information available about required documents for {service.name}."
                
                # Create an interaction record
                interaction = UserInteraction(
                    user_id=user.id,
                    service_id=service.id,
                    interaction_type='information_request',
                    status='completed'
                )
                db.session.add(interaction)
                db.session.commit()
            else:
                if user.language_preference == 'rw':
                    message = "Mbabarira, sinabashije kubona amakuru kuri serivisi wasabye."
                else:
                    message = "Sorry, I couldn't find information about the requested service."
        else:
            if user.language_preference == 'rw':
                message = f"Sinabonye {service_type or 'serivisi'} hafi yawe. Gerageza indi."
            else:
                message = f"I couldn't find any {service_type or 'services'} near you. Please try again."
    
    else:
        # We need more information
        if user.language_preference == 'rw':
            message = "Kugirango ndebe amakuru yiyi serivisi, nahitaji kumenya ubuhe bwoko bwa serivisi n'aho uherereye."
        else:
            message = "To check service information, I need to know what type of service and your location."
    
    # Send the response
    sms_service.send_response(user, conversation, message)
    return True

def connect_call_to_service(user, conversation, entities):
    """Connect user to a service via phone call"""
    # This is a placeholder for the actual implementation
    # In a real system, this would initiate a call via the voice API
    
    if user.language_preference == 'rw':
        message = "Mbabarira, guhuza uwatakumbusa na serivisi bidashoboka kuri ubu."
    else:
        message = "Sorry, connecting calls to services is not available in this prototype."
    
    # Send the response
    sms_service.send_response(user, conversation, message)
    return True

def process_follow_up_reply(user, conversation, intent, message_text):
    """Process user's reply to a follow-up message"""
    # Process the follow-up response
    result = scheduler_service.process_follow_up_response(user.id, message_text)
    
    if result:
        if intent == 'confirm_service':
            if user.language_preference == 'rw':
                response = "Murakoze! Twishimye ko wabonye service yawe neza."
            else:
                response = "Thank you! We're glad you received the service successfully."
        else:  # deny_service
            if user.language_preference == 'rw':
                response = "Mbabarira ko wabonye ibibazo! Turaza gukurikirana iyi kibazo."
            else:
                response = "We're sorry you encountered issues! We'll follow up on this."
    else:
        if user.language_preference == 'rw':
            response = "Murakoze ko wadushubije."
        else:
            response = "Thank you for your response."
    
    # Send the response
    sms_service.send_response(user, conversation, response)
    return True

def send_help_information(user, conversation):
    """Send help information to the user"""
    if user.language_preference == 'rw':
        message = """Ubu ni bumwe mu buryo wakoresha Tugendane:

1. Gushaka serivisi: "Ndashaka ivuriro hafi"
2. Kubona inzira: "Amabwiriza yo kujya ku biro by'umurenge"
3. Gusesengura amasaha: "Ni ryari minisiteri ifungurwa?"
4. Impapuro zisabwa: "Ni ibihe byangombwa bisabwa kubona passport?"

Shyiramo SMS yawe mu rurimi urwo aricyo cyose (Icyongereza cyangwa Ikinyarwanda).
"""
    else:
        message = """Here are some ways you can use Tugendane:

1. Find a service: "I need a health clinic nearby"
2. Get directions: "Directions to the sector office"
3. Check hours: "When is the ministry open?"
4. Required documents: "What documents do I need for a passport?"

You can send your SMS in either English or Kinyarwanda.
"""
    
    # Send the response
    sms_service.send_response(user, conversation, message)
    return True

def send_default_response(user, conversation):
    """Send a default response when intent is not recognized"""
    if user.language_preference == 'rw':
        message = "Mbabarira, sinumvise neza icyo ushaka. Nshobora kugufasha gushaka serivisi za guverinoma, gutanga amabwiriza, n'ibindi. Tanga andi makuru, cyangwa andika 'HELP' kugirango ubone urutonde rw'amabwiriza."
    else:
        message = "Sorry, I didn't understand what you're looking for. I can help you find government services, provide directions, and more. Please provide more details, or type 'HELP' to see a list of instructions."
    
    # Send the response
    sms_service.send_response(user, conversation, message)
    return True
