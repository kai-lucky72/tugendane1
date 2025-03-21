from datetime import datetime
from geoalchemy2 import Geometry
from app import db
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Index, func, Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship

class GovernmentService(db.Model):
    """Model for government services (clinics, offices, etc.)"""
    __tablename__ = 'government_services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # health, education, social services, etc.
    description = db.Column(db.Text)
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(255))
    opening_hours = db.Column(db.String(255))  # Stored as string like "Mon-Fri: 8:00-17:00"
    required_documents = db.Column(db.Text)

    # Location data
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Additional data as JSON
    service_metadata = db.Column(JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    interactions = relationship("UserInteraction", back_populates="service")

    def __repr__(self):
        return f"<GovernmentService {self.name} ({self.category})>"

    @property
    def latitude(self):
        """Extract latitude from the geometry point"""
        #This will need to be updated once the location column is fixed
        return None

    @property
    def longitude(self):
        """Extract longitude from the geometry point"""
        #This will need to be updated once the location column is fixed
        return None

# Create spatial index on location column
#Index('idx_government_services_location', GovernmentService.location, postgresql_using='gist')

class User(db.Model):
    """Model for system users (citizens)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    language_preference = db.Column(db.String(10), default='en')  # 'en' for English, 'rw' for Kinyarwanda

    # Last known location (optional)
    last_latitude = db.Column(db.Float)
    last_longitude = db.Column(db.Float)
    last_location_timestamp = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    interactions = relationship("UserInteraction", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

    def __repr__(self):
        return f"<User {self.phone_number}>"

class UserInteraction(db.Model):
    """Model for tracking user interactions with services"""
    __tablename__ = 'user_interactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('government_services.id'), nullable=False)

    interaction_type = db.Column(db.String(50), nullable=False)  # 'inquiry', 'direction_request', 'call_connection', etc.
    status = db.Column(db.String(50), nullable=False)  # 'in_progress', 'completed', 'canceled'

    # For follow-up tracking
    follow_up_scheduled = db.Column(db.Boolean, default=False)
    follow_up_sent = db.Column(db.Boolean, default=False)
    follow_up_sent_at = db.Column(db.DateTime)
    follow_up_response = db.Column(db.Text)
    follow_up_response_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="interactions")
    service = relationship("GovernmentService", back_populates="interactions")

    def __repr__(self):
        return f"<UserInteraction {self.interaction_type} User:{self.user_id} Service:{self.service_id}>"

class Message(db.Model):
    """Model for storing messages in conversations"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)

    sender_type = db.Column(db.String(10), nullable=False)  # 'user' or 'system'
    message_type = db.Column(db.String(20), nullable=False)  # 'sms', 'voice', 'web'
    content = db.Column(db.Text, nullable=False)

    # NLP analysis results
    intent = db.Column(db.String(100))
    entities = db.Column(JSON)
    language = db.Column(db.String(10))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id} {self.sender_type}:{self.message_type}>"

class Conversation(db.Model):
    """Model for tracking conversations with users"""
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    channel = db.Column(db.String(20), nullable=False)  # 'sms', 'voice', 'web'
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'completed', 'expired'

    # Current conversation state (for stateful conversations)
    current_state = db.Column(db.String(50))
    context = db.Column(JSON)  # Stores any context needed for the conversation

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation {self.id} User:{self.user_id} Channel:{self.channel}>"