# Profile Integration API

A Django-based REST API that integrates with external APIs (Genderize, Agify, Nationalize) to create and manage user profiles with demographic information. Stage 2 adds advanced filtering, sorting, pagination, and natural language search capabilities.

---

## Features

### Core Features

- Create profiles with automatic data fetching from three external APIs
- Idempotent profile creation (same name returns existing profile)
- Retrieve single or multiple profiles with filtering
- Delete profiles
- UUID v7 for unique identifiers
- Comprehensive error handling and logging
- CORS enabled for cross-origin requests

### Stage 2 New Features

- **Advanced Filtering**: Filter by gender, age_group, country_id, age range, and probability scores
- **Sorting**: Sort by age, created_at, or gender_probability (ascending/descending)
- **Pagination**: Page through results with configurable page size (max 50)
- **Natural Language Search**: Query profiles using plain English phrases
- **Rule-based Query Parsing**: Convert natural language into structured filters without AI/LLM

---

## API Endpoints

### 1. Create Profile

**POST** `/api/profiles/`

**Request Body**

```json
{
  "name": "ella"
}
```

**Success Response (201 Created)**

```json
{
  "status": "success",
  "data": {
    "id": "019db50a-d637-4263-aae5-38e49aea85d0",
    "name": "ella",
    "gender": "female",
    "gender_probability": 0.99,
    "age": 46,
    "age_group": "adult",
    "country_id": "NG",
    "country_name": "Nigeria",
    "country_probability": 0.85,
    "created_at": "2026-04-22T11:54:39.544218Z"
  }
}
```

**If profile already exists (200 OK)**

```json
{
  "status": "success",
  "message": "Profile already exists",
  "data": {}
}
```

---

### 2. Get All Profiles

**GET** `/api/profiles/`

**Query Parameters**

| Parameter               | Type    | Description                           |
| ----------------------- | ------- | ------------------------------------- |
| gender                  | string  | male/female                           |
| age_group               | string  | child/teenager/adult/senior           |
| country_id              | string  | NG, KE, US, etc.                      |
| min_age                 | integer | Minimum age                           |
| max_age                 | integer | Maximum age                           |
| min_gender_probability  | float   | 0–1                                   |
| min_country_probability | float   | 0–1                                   |
| sort_by                 | string  | age / created_at / gender_probability |
| order                   | string  | asc / desc                            |
| page                    | integer | default 1                             |
| limit                   | integer | default 10, max 50                    |

**Example**

```
GET /api/profiles/?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

---

### 3. Get Single Profile

**GET** `/api/profiles/{id}/`

---

### 4. Delete Profile

**DELETE** `/api/profiles/{id}/`
**Response:** 204 No Content

---

### 5. Natural Language Search

**GET** `/api/profiles/search/?q=your_query`

**Examples**

```
young males from nigeria
females above 30
adult males from kenya
```

---

### 6. Health Check

**GET** `/health/`

```json
{
  "status": "ok",
  "message": "Profile Integration API is running"
}
```

---

## Natural Language Parsing

Uses **rule-based pattern matching** (no AI/LLM).

### Example Mappings

| Query                    | Result                                   |
| ------------------------ | ---------------------------------------- |
| young males from nigeria | gender=male, age 16–24, country=NG       |
| females above 30         | gender=female, min_age=30                |
| adult males from kenya   | gender=male, age_group=adult, country=KE |

### Limitations

- No AND/OR logic
- No negation
- Single country detection
- No typo correction
- Limited keyword mapping

---

## Error Format

```json
{
  "status": "error",
  "message": "Error message"
}
```

| Code | Meaning            |
| ---- | ------------------ |
| 400  | Bad request        |
| 404  | Not found          |
| 422  | Invalid query      |
| 500  | Server error       |
| 502  | External API error |

---

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL

---

### 1. Clone Project

```bash
git clone <repository-url>
cd Profile-Integration
```

---

### 2. Create Virtual Environment

```bash
python -m venv venv
```

**Activate**

```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Install Required Packages (if no requirements.txt yet)

```bash
pip install django djangorestframework psycopg2-binary requests drf-yasg django-cors-headers python-dotenv gunicorn
```

---

### 5. Setup Environment Variables

```bash
cp .env.example .env
```

Example `.env`:

```
DB_NAME=mnc_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

SECRET_KEY=your_secret_key
DEBUG=True
```

---

### 6. Run Migrations

```bash
python manage.py migrate
```

---

### 7. Seed Database (Optional)

```bash
python manage.py seed_profiles --source sample
```

---

### 8. Run Server

```bash
python manage.py runserver
```

---

## Docker (Optional)

```bash
docker compose up --build
```

---

## Deployment

```
https://rofile--ntegration-adewumijosephine3516-kodp7ruz.leapcell.dev
```

---

## API Docs

```
/api/docs/
```

---

## Testing

```bash
curl.exe "https://your-api.com/api/profiles/?gender=male&page=1&limit=10"

curl.exe "https://your-api.com/api/profiles/search/?q=young%20males%20from%20nigeria"

Invoke-RestMethod -Uri "https://your-api.com/api/profiles/" -Method POST -ContentType "application/json" -Body '{"name":"testuser"}'
```

---

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- drf-yasg
- Gunicorn
- Requests
- django-cors-headers

---

## Author

Backend Wizard - Josseycodes

---

## License

MIT
