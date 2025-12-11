# FastAPI Migration Project

FastAPI migration of LoanCalculator2 backend from Django.

## Setup

1. Activate virtual environment:
   
   .\venv\Scripts\Activate.ps1
   2. Install dependencies:hell
   pip install -r requirements.txt
   3. Create `.env` file from `.env.example` and fill in your values

4. Run the application:
   
   python -m app.main
      Or using uvicorn directly:
   uvicorn app.main:app --reload
   ## Project Structure

- `app/main.py` - FastAPI application entry point
- `app/config.py` - Configuration settings
- `app/database.py` - Database connection and session management
- `app/dependencies.py` - Shared dependencies
- `app/apps/` - Application modules (authentication, client, product, quote, etc.)
- `app/common/` - Common utilities
- `app/middleware/` - Middleware (CORS, etc.)

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check

More endpoints will be added as modules are migrated.