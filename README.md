# Solar CRM

A purpose-built CRM for residential and commercial solar installation businesses in India, focusing on lead acquisition, call outcomes, site surveys, and quotation negotiations up to the "Won" milestone.

## Technology Stack

- **Backend**: Python 3.12+, Django 5, Django REST Framework, SimpleJWT, drf-spectacular, django-cors-headers, django-filter, APScheduler, python-dotenv, psycopg (v3)
- **Frontend**: React 18+, Vite, TypeScript, Mantine UI, TanStack Query, React Router, Axios
- **Database**: PostgreSQL 16+ (Local installation)

## Core Business Rule

> **Every call, visit, or message must end with an outcome.**
> Each outcome sets three things:
> 1. The **lead status**
> 2. The **next action**
> 3. The **next follow-up date**
>
> A lead with no next follow-up date is never allowed (except terminal statuses: `Won`, `Lost`, `Do not contact`, `Merged`, `Invalid contact`).

## Project Structure

```
solar-crm/
  backend/          # Django project ("config") & apps
    accounts/       # Custom user model with roles (admin, manager, salesperson, surveyor)
    masters/        # Outcome matrix, Lost/Nurture reasons, Lead sources, Policy settings
    leads/          # Core lead management & status transition history
    activities/     # Follow-up logs (calls, WhatsApp, visits, notes)
    surveys/        # Site surveys, schedule tracking, and site photos
    quotes/         # Versioned solar proposals (never deleted or overwritten)
  frontend/         # Vite React TypeScript application with Mantine UI
  docs/             # Process definition & official User Manual (USER_MANUAL.md)
  .gitignore
  README.md
```

## Documentation
- Detailed Operations & User Manual: [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)
- Process Definition: `docs/Solar CRM – All Process Paths and Outcomes (v0.1).pdf`

## Getting Started

### 1. Database Setup
Create database `solar_crm` and user `solar_user` in your local PostgreSQL:
```sql
CREATE USER solar_user WITH PASSWORD 'your_password';
CREATE DATABASE solar_crm OWNER solar_user;
```

### 2. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env # Update with your DB credentials
python manage.py migrate
python manage.py seed_masters
python manage.py runserver
```
- Swagger API Docs: `http://localhost:8000/api/docs/`
- Health check: `http://localhost:8000/api/health/`
- Django Admin: `http://localhost:8000/admin/`

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`.
