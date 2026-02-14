# Recruitment SaaS Platform - Backend

FastAPI backend for the recruitment SaaS platform.

## Setup

### 1. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and set your configuration
```

### 4. Run MongoDB
Make sure MongoDB is running on `localhost:27017` or update the `MONGODB_URL` in `.env`.

### 5. Run the application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration settings
├── database.py          # MongoDB connection
├── models/              # Database models
│   └── user.py
├── schemas/             # Request/Response schemas
│   └── auth.py
├── routers/             # API endpoints
│   └── auth.py
└── utils/               # Utilities
    ├── security.py      # Password hashing, JWT
    └── dependencies.py  # Auth dependencies
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register organization + admin user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user

## Development

Run with auto-reload:
```bash
uvicorn app.main:app --reload
```

## Testing

```bash
pytest
```
