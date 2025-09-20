# Motor Backend FastAPI

A FastAPI backend application for motor management system with PostgreSQL 17 database.

## Features

- FastAPI framework with async support
- PostgreSQL 17 database with async SQLAlchemy
- Alembic for database migrations
- Docker and Docker Compose setup
- Health check endpoints
- CORS middleware support

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository and navigate to the project directory
2. Run the application using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL 17 database on port 5432
- FastAPI application on port 8000

### Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the application is running, you can access:
- Interactive API docs: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Database

The application uses PostgreSQL 17 with the following default configuration:
- Host: localhost (or `db` in Docker)
- Port: 5432
- Database: motor_backend
- Username: postgres
- Password: postgres

## Project Structure

```
app/
├── api/
│   └── v1/
│       └── endpoints/     # API endpoints
├── core/
│   ├── config.py         # Configuration settings
│   └── database.py       # Database connection
├── crud/                 # Database operations
├── models/               # SQLAlchemy models
├── schemas/              # Pydantic schemas
└── services/             # Business logic
```

## Development

### Adding New Endpoints

1. Create a new router in `app/api/v1/endpoints/`
2. Import and include the router in `app/main.py`

### Database Migrations

1. Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

2. Apply migrations:
```bash
alembic upgrade head
```

## Docker Commands

- Start services: `docker-compose up -d`
- Stop services: `docker-compose down`
- View logs: `docker-compose logs -f`
- Rebuild: `docker-compose up --build`
