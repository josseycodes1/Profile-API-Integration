# Profile Integration API

A Django-based REST API that integrates with external APIs (Genderize, Agify, Nationalize) to create and manage user profiles with demographic information.

## Features

- Create profiles with automatic data fetching from three external APIs
- Idempotent profile creation (same name returns existing profile)
- Retrieve single or multiple profiles with filtering
- Delete profiles
- Case-insensitive filtering by gender, country, and age group
- UUID v7 for unique identifiers
- Comprehensive error handling and logging
- CORS enabled for cross-origin requests

## API Endpoints

### Create Profile

`POST /api/profiles`

```json
{
  "name": "ella"
}
Get Single Profile
GET /api/profiles/{id}

Get All Profiles
GET /api/profiles?gender=male&country_id=NG&age_group=adult

Delete Profile
DELETE /api/profiles/{id}

Installation
Clone the repository:

bash
git clone <repository-url>
cd Profile-Integration
Create virtual environment:

bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies:

bash
pip install -r requirements.txt
Set up environment variables:

bash
cp .env.example .env
# Edit .env with your database credentials
Run migrations:

bash
python manage.py migrate
Start the server:

bash
python manage.py runserver
Deployment on Leapcell
Push code to GitHub repository

Connect repository to Leapcell
Set environment variables in Leapcell dashboard
Deploy with Procfile and runtime.txt

Testing
bash
python manage.py test

## Environment Variables
DB_NAME: PostgreSQL database name
DB_USER: Database user
DB_PASSWORD: Database password
DB_HOST: Database host
DB_PORT: Database port
DB_SSLMODE: SSL mode (require/prefer)
SECRET_KEY: Django secret key
DEBUG: Set to False in production
ALLOWED_HOSTS: Comma-separated list of allowed hosts

## Error Handling
The API returns appropriate HTTP status codes:
200: Success
201: Created
204: No Content (Delete success)
400: Bad Request (Missing name)
404: Not Found
422: Unprocessable Entity (Invalid type)
500: Internal Server Error
502: Bad Gateway (External API error)

## Logging
Logs are stored in logs/django.log and include:
API request/response details
External API call status
Error traces
Database operations

## Technologies
Django 4.2.7
PostgreSQL
Gunicorn (production server)
Requests (external API calls)
django-cors-headers
```
