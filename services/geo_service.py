import logging
import json
import requests
from flask import current_app
from sqlalchemy import func
from app import db
from models import GovernmentService

logger = logging.getLogger(__name__)

class GeoService:
    """Service for geographic operations and routing"""
    
    def __init__(self, app=None):
        self.app = app
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        self.graphhopper_api_key = app.config.get('GRAPHHOPPER_API_KEY')
        self.search_radius = app.config.get('SERVICE_SEARCH_RADIUS_KM', 10)
    
    def find_nearest_services(self, latitude, longitude, service_category=None, limit=5):
        """Find the nearest government services based on coordinates and category"""
        try:
            # Convert kilometers to approximate degrees for the query
            # This is a rough approximation that works for small distances
            radius_degrees = self.search_radius / 111.0  # ~111km per degree at the equator
            
            # Build the query
            query = db.session.query(GovernmentService)
            
            # Add PostGIS distance calculation
            distance = func.ST_Distance(
                func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
                GovernmentService.location
            )
            
            query = query.add_columns(distance.label('distance'))
            
            # Filter by category if provided
            if service_category:
                query = query.filter(GovernmentService.category == service_category)
            
            # Filter by distance
            query = query.filter(
                func.ST_DWithin(
                    func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
                    GovernmentService.location,
                    radius_degrees
                )
            )
            
            # Order by distance and limit results
            query = query.order_by(distance).limit(limit)
            
            # Execute query
            results = query.all()
            
            # Format the results
            services = []
            for service, distance in results:
                # Convert distance from degrees to kilometers (approximate)
                distance_km = distance * 111.0
                
                services.append({
                    'id': service.id,
                    'name': service.name,
                    'category': service.category,
                    'address': service.address,
                    'phone_number': service.phone_number,
                    'opening_hours': service.opening_hours,
                    'latitude': service.latitude,
                    'longitude': service.longitude,
                    'distance_km': round(distance_km, 2)
                })
            
            return services
            
        except Exception as e:
            logger.error(f"Error finding nearest services: {e}")
            return []
    
    def get_directions(self, from_lat, from_lng, to_lat, to_lng, language='en'):
        """Get directions from one point to another using GraphHopper"""
        try:
            # Check if API key is available
            if not self.graphhopper_api_key:
                logger.error("GraphHopper API key not configured")
                return None
            
            # Build the API request
            url = "https://graphhopper.com/api/1/route"
            params = {
                'point': [f"{from_lat},{from_lng}", f"{to_lat},{to_lng}"],
                'vehicle': 'foot',  # Default to walking directions
                'locale': 'en' if language == 'en' else 'fr',  # Using French as proxy for Kinyarwanda
                'details': 'time|distance',
                'instructions': 'true',
                'key': self.graphhopper_api_key
            }
            
            # Make the API request
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract the path information
                if 'paths' in data and len(data['paths']) > 0:
                    path = data['paths'][0]
                    
                    # Format the instructions
                    instructions = []
                    if 'instructions' in path:
                        for instruction in path['instructions']:
                            instructions.append({
                                'text': instruction.get('text', ''),
                                'distance': instruction.get('distance', 0),
                                'time': instruction.get('time', 0),
                                'sign': instruction.get('sign', 0)
                            })
                    
                    # Prepare the result
                    directions = {
                        'distance': path.get('distance', 0),
                        'time': path.get('time', 0),
                        'instructions': instructions
                    }
                    
                    return directions
                
                logger.warning("No path found in the directions response")
                return None
                
            else:
                logger.error(f"GraphHopper API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            return None
    
    def format_directions_text(self, directions, language='en'):
        """Format directions into a human-readable text"""
        if not directions or 'instructions' not in directions:
            if language == 'en':
                return "Directions are not available at the moment."
            else:  # Kinyarwanda
                return "Amabwiriza ntabwo abonetse kuri iyi saha."
        
        # Start building the directions text
        total_distance = directions.get('distance', 0) / 1000  # Convert to km
        total_time = directions.get('time', 0) / 60000  # Convert to minutes
        
        if language == 'en':
            text = f"Total journey: {total_distance:.1f} kilometers, approximately {total_time:.0f} minutes walking.\n\n"
        else:  # Kinyarwanda
            text = f"Urugendo rwose: {total_distance:.1f} kilometero, hafi {total_time:.0f} iminota agenda n'amaguru.\n\n"
        
        # Add step-by-step instructions
        instruction_texts = []
        for i, instruction in enumerate(directions['instructions']):
            distance = instruction.get('distance', 0)
            
            # Skip very short segments
            if distance < 10 and i > 0 and i < len(directions['instructions']) - 1:
                continue
            
            instruction_text = instruction.get('text', '')
            
            if distance >= 1000:
                distance_text = f"{distance/1000:.1f} km"
            else:
                distance_text = f"{int(distance)} m"
            
            if language == 'en':
                formatted_text = f"{i+1}. {instruction_text} ({distance_text})"
            else:  # Kinyarwanda
                # Simple translation for demonstration
                if "Turn left" in instruction_text:
                    instruction_text = instruction_text.replace("Turn left", "Hindukira ibumoso")
                elif "Turn right" in instruction_text:
                    instruction_text = instruction_text.replace("Turn right", "Hindukira iburyo")
                elif "Continue" in instruction_text:
                    instruction_text = instruction_text.replace("Continue", "Komeza")
                
                formatted_text = f"{i+1}. {instruction_text} ({distance_text})"
            
            instruction_texts.append(formatted_text)
        
        # Join all instructions
        text += "\n".join(instruction_texts)
        
        return text
    
    def geocode_location(self, location_name):
        """Convert a location name to coordinates using Nominatim (OpenStreetMap)"""
        try:
            # Add Rwanda as default region
            search_text = f"{location_name}, Rwanda"
            
            # Use Nominatim geocoding API
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': search_text,
                'format': 'json',
                'limit': 1
            }
            
            headers = {
                'User-Agent': 'Tugendane-Service-Locator'
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    result = data[0]
                    
                    return {
                        'latitude': float(result['lat']),
                        'longitude': float(result['lon']),
                        'display_name': result['display_name']
                    }
                
                logger.warning(f"Location not found: {location_name}")
                return None
                
            else:
                logger.error(f"Geocoding API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error geocoding location: {e}")
            return None
