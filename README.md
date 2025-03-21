# Tugendane - AI Agent for Rwandan Government Services

Tugendane is an AI-powered system designed to help Rwandan citizens access nearby government services via SMS, voice calls, and a web interface. The system works both online and offline, providing service lookup, locational guidance, service availability verification, call connection, and follow-up confirmation.

![Tugendane Banner](https://raw.githubusercontent.com/kai-lucky72/tugendane/main/static/img/banner.jpg)

## Features

- **Multi-channel Access**: Access government services via SMS, voice calls, or web interface
- **NLP Processing**: Natural language processing to understand user requests in both English and Kinyarwanda
- **Geographic Service Lookup**: Find the nearest government services based on user location
- **Step-by-Step Directions**: Get text-based directions to services
- **Service Information**: Check operating hours and required documents
- **Follow-up System**: Confirmation and feedback mechanism after service usage
- **Admin Dashboard**: Monitor system usage and analyze interactions

## Architecture

Tugendane is built with the following components:

- **Backend**: Python with Flask for API endpoints and web interface
- **Database**: PostgreSQL with PostGIS for geographic queries
- **NLP Engine**: spaCy for intent and entity recognition
- **SMS Gateway**: Africa's Talking SMS API
- **Voice Processing**: Africa's Talking Voice API with Speech-to-Text capabilities
- **Geolocation & Routing**: OpenStreetMap data with GraphHopper routing
- **Task Scheduling**: Celery with Redis for follow-up messages

## System Requirements

- Python 3.9+
- PostgreSQL with PostGIS extension
- Redis (for Celery task queue)
- Africa's Talking API account
- GraphHopper API key (optional)

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/kai-lucky72/tugendane.git
cd tugendane
