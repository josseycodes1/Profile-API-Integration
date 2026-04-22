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

## Natural Language Query Parsing

### Approach

The natural language parser uses rule-based pattern matching to convert plain English queries into structured filters.

### Supported Keywords and Mappings

#### Gender

- Male: "male", "man", "men", "boy", "boys"
- Female: "female", "woman", "women", "girl", "girls"

#### Age Groups

- "child" → ages 0-12
- "teenager"/"teen"/"teens" → ages 13-19
- "adult"/"adults" → ages 20-59
- "senior"/"seniors"/"elderly"/"old" → ages 60+

#### Special Age Mappings

- "young" → ages 16-24 (not stored as age_group)
- "middle aged" → ages 35-55

#### Age Comparisons

- "above X", "over X", "older than X" → min_age = X
- "below X", "under X", "younger than X" → max_age = X
- "between X and Y" → min_age = X, max_age = Y

#### Countries

- Supports 30+ countries including: Nigeria(NG), Ghana(GH), Kenya(KE), South Africa(ZA), etc.

#### Confidence/Probability

- "high confidence" → min probability = 0.8
- "confident" → min probability = 0.7
- "probability above X" → min probability = X

### Example Queries

| Query                         | Mapped Filters                                     |
| ----------------------------- | -------------------------------------------------- |
| "young males from nigeria"    | gender=male, min_age=16, max_age=24, country_id=NG |
| "females above 30"            | gender=female, min_age=30                          |
| "adult males from kenya"      | gender=male, age_group=adult, country_id=KE        |
| "teenagers between 15 and 18" | age_group=teenager, min_age=15, max_age=18         |
| "high confidence females"     | gender=female, min_gender_probability=0.8          |

### Limitations

- Does not handle complex boolean logic (AND/OR combinations)
- Cannot process negation (e.g., "not from nigeria")
- Limited to single country detection
- Age ranges are inclusive
- No support for relative time (e.g., "recent profiles")
- Country names must match predefined list
- Does not handle misspellings or synonyms beyond defined keywords
- Cannot process queries with multiple conflicting conditions

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
