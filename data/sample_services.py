import logging
from sqlalchemy import func
from app import db
from models import GovernmentService
from geoalchemy2.elements import WKTElement

logger = logging.getLogger(__name__)

def import_sample_services():
    """Import sample government services data into the database"""
    try:
        # Define sample services with coordinates in Rwanda
        # Coordinates are in the format (latitude, longitude)
        sample_services = [
            {
                "name": "Kigali Central Hospital",
                "category": "health",
                "description": "Main public hospital in Kigali",
                "phone_number": "+250700000001",
                "email": "info@kch.gov.rw",
                "address": "KN 4 Ave, Kigali",
                "opening_hours": "24/7",
                "required_documents": "ID card, health insurance card",
                "latitude": -1.944519,
                "longitude": 30.059114
            },
            {
                "name": "Nyamirambo Health Center",
                "category": "health",
                "description": "Community health center",
                "phone_number": "+250700000002",
                "email": "info@nyamirambo-hc.gov.rw",
                "address": "Nyamirambo, Kigali",
                "opening_hours": "Mon-Fri: 7:00-17:00, Sat: 8:00-12:00",
                "required_documents": "ID card, health insurance card",
                "latitude": -1.985465,
                "longitude": 30.044865
            },
            {
                "name": "Kigali City Hall",
                "category": "administration",
                "description": "City administration headquarters",
                "phone_number": "+250700000003",
                "email": "info@kigalicity.gov.rw",
                "address": "KN 2 Ave, Kigali",
                "opening_hours": "Mon-Fri: 8:00-17:00",
                "required_documents": "ID card",
                "latitude": -1.950214,
                "longitude": 30.061645
            },
            {
                "name": "Rwanda Immigration Office",
                "category": "identification",
                "description": "Passport and visa services",
                "phone_number": "+250700000004",
                "email": "info@immigration.gov.rw",
                "address": "KG 626 St, Kigali",
                "opening_hours": "Mon-Fri: 7:00-17:00",
                "required_documents": "ID card, passport application form, photos, payment receipt",
                "latitude": -1.943837,
                "longitude": 30.089948
            },
            {
                "name": "Rwanda Revenue Authority - Kigali Branch",
                "category": "taxation",
                "description": "Tax services and payments",
                "phone_number": "+250700000005",
                "email": "info@rra.gov.rw",
                "address": "KN 4 Ave, Kigali",
                "opening_hours": "Mon-Fri: 8:00-16:00",
                "required_documents": "ID card, TIN certificate, tax forms",
                "latitude": -1.953671,
                "longitude": 30.062544
            },
            {
                "name": "Remera Police Station",
                "category": "security",
                "description": "Police services for Remera sector",
                "phone_number": "+250700000006",
                "email": "remera@police.gov.rw",
                "address": "KG 11 Ave, Remera, Kigali",
                "opening_hours": "24/7",
                "required_documents": "ID card",
                "latitude": -1.950399,
                "longitude": 30.106071
            },
            {
                "name": "Nyarugenge District Office",
                "category": "administration",
                "description": "District administration services",
                "phone_number": "+250700000007",
                "email": "info@nyarugenge.gov.rw",
                "address": "KN 31 St, Nyarugenge, Kigali",
                "opening_hours": "Mon-Fri: 7:00-17:00",
                "required_documents": "ID card",
                "latitude": -1.960411,
                "longitude": 30.054695
            },
            {
                "name": "RSSB Headquarters",
                "category": "social",
                "description": "Social security and health insurance services",
                "phone_number": "+250700000008",
                "email": "info@rssb.rw",
                "address": "KN 3 Rd, Kigali",
                "opening_hours": "Mon-Fri: 7:00-17:00",
                "required_documents": "ID card, employer registration documents",
                "latitude": -1.949345,
                "longitude": 30.065351
            },
            {
                "name": "University of Rwanda - College of Business",
                "category": "education",
                "description": "Public university",
                "phone_number": "+250700000009",
                "email": "info@ur.ac.rw",
                "address": "KN 7 Ave, Kigali",
                "opening_hours": "Mon-Fri: 8:00-18:00, Sat: 8:00-12:00",
                "required_documents": "ID card, academic certificates",
                "latitude": -1.941681,
                "longitude": 30.059841
            },
            {
                "name": "Kigali Public Library",
                "category": "education",
                "description": "Public library services",
                "phone_number": "+250700000010",
                "email": "library@kigalicity.gov.rw",
                "address": "KG 13 Ave, Kigali",
                "opening_hours": "Mon-Sat: 9:00-18:00",
                "required_documents": "ID card",
                "latitude": -1.956764,
                "longitude": 30.099733
            }
        ]

        # Add services to the database
        for service_data in sample_services:
            # Create PostGIS POINT from coordinates - corrected coordinate order
            location = WKTElement(f"POINT({service_data['longitude']} {service_data['latitude']})", srid=4326)
            service_data.pop('latitude')
            service_data.pop('longitude')

            # Create the service object
            service = GovernmentService(
                location=location,
                **service_data
            )

            db.session.add(service)

        # Commit changes
        db.session.commit()
        logger.info(f"Successfully imported {len(sample_services)} sample services")
        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing sample services: {e}")
        return False

# Contact number for AI agent:  This would need to be configured appropriately.  For this example, I'm leaving it as a placeholder.
# contact_number = "+15551234567"  Replace with the actual contact number