from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.utils.logging_config import setup_logging, logger
from app.api.routes import (
    health, assets, asset_types, owners, locations,
    shipments, custody, returns, inspections, repairs,
    deposits, validation, analytics
)

setup_logging()

app = FastAPI(
    title="ReturnFlow API",
    description="Reusable Asset Return & Lifecycle Management System - High-throughput REST API for asset tracking, custody traceability, and financial reconciliation.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system administrator."}
    )

# Include API Routers
app.include_router(health.router)
app.include_router(assets.router)
app.include_router(asset_types.router)
app.include_router(owners.router)
app.include_router(locations.router)
app.include_router(shipments.router)
app.include_router(custody.router)
app.include_router(returns.router)
app.include_router(inspections.router)
app.include_router(repairs.router)
app.include_router(deposits.router)
app.include_router(validation.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to ReturnFlow - Reusable Asset Return & Lifecycle Management API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
