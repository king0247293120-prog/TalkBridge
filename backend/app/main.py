from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.routers.writing import router as writing_router
from app.routers.documents import router as documents_router
from app.core.config import settings
from app.database.database import engine
from app.database.init_db import init_db
from app.routers.translation import router as translation_router
from app.routers.image import router as image_router
from app.routers.speech import router as speech_router
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(speech_router)
app.include_router(documents_router)
app.include_router(translation_router)
app.include_router(image_router)
app.include_router(writing_router)
@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def home():
    return {
        "name": "TalkBridge",
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "status": "online",
        "message": "Welcome to TalkBridge 2.0",
        "ai_provider": "Open-source models",
        "database": "SQLite",
        "features": [
            "Translation Intelligence",
            "Image Intelligence",
            "Writing Intelligence",
            "Document Intelligence",
            "Speech Intelligence",
            "Dictionary Intelligence",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "TalkBridge",
    }


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "SQLite",
            "message": "Database connection successful.",
        }

    except Exception as error:
        return {
            "status": "error",
            "database": "SQLite",
            "message": str(error),
        }