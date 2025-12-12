"""
FastAPI application entry point
Main application initialization
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.config import DEBUG, MODE
from app.middleware.cors import setup_cors
from app.database import init_db, close_db
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Loan Calculator API",
    description="FastAPI migration of LoanCalculator2 backend",
    version="0.1.0",
    debug=DEBUG,
)

# Setup CORS
setup_cors(app)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info(f"Starting application in {MODE} mode")
    # Uncomment when models are ready
    # await init_db()
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    logger.info("Shutting down application")
    await close_db()
    logger.info("Application shut down successfully")


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return JSONResponse({
        "message": "Loan Calculator API",
        "version": "0.1.0",
        "mode": MODE,
        "status": "running"
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "mode": MODE
    })


# Include routers here as you create them
from app.apps.authentication.router import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])

from app.apps.advisor.router import router as advisor_router
app.include_router(advisor_router, prefix="/api/advisor", tags=["advisor"])

from app.apps.client.router import router as client_router
app.include_router(client_router, prefix="/api/client", tags=["client"])

from app.apps.product.router import router as product_router
# Use /product prefix to match frontend expectations (without /api)
app.include_router(product_router, prefix="/api/product", tags=["product"])

from app.apps.quote.router import router as quote_router
app.include_router(quote_router, prefix="/api/quote", tags=["quote"])

from app.apps.loan.router import router as loan_router
app.include_router(loan_router, prefix="/api/loan", tags=["loan"])

from app.apps.cms.router import router as cms_router
app.include_router(cms_router, prefix="/api/cms", tags=["cms"])


if __name__ == "__main__":
    import uvicorn
    import os
    # Allow port to be configured via environment variable, default to 5000 to match frontend
    port = int(os.getenv("PORT", "5000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    )