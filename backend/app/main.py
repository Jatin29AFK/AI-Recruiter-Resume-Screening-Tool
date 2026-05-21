import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.matcher import router as matcher_router
from app.routes.jobs import router as jobs_router
from app.routes.notes import router as notes_router

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AI Resume Job Matcher API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Hybrid AI Resume–Job Matcher backend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matcher_router)
app.include_router(jobs_router)
app.include_router(notes_router)

@app.get("/")
def root():
    return {
        "message": f"{APP_NAME} backend is running",
        "docs": "/docs",
        "version": APP_VERSION
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "resume-matcher-api",
        "version": APP_VERSION
    }