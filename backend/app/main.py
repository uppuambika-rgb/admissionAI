from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from app.config import settings
from app.models.student import StudentProfile, ChatRequest, ChatResponse
from app.models.program import CollegeProgram, RecommendationResponse
from app.services.ranker import load_college_programs, generate_recommendations
from app.services.ai_counsellor import generate_chat_reply, enrich_explanations_with_ai

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Admission Counselling Agent with deterministic eligibility engine and conversational guidance."
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hackathon-friendly: allows Vite / localhost dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Check for frontend build
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "gemini_configured": bool(settings.GEMINI_API_KEY)}


@app.get("/api/programs", response_model=List[CollegeProgram])
def get_programs():
    """Returns all college programs in the mock database."""
    return load_college_programs()

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Conversational admission counsellor endpoint.
    Extracts student profile attributes and returns guided dialogue.
    """
    profile = request.current_profile or StudentProfile()
    return generate_chat_reply(
        message=request.message,
        history=request.history,
        current_profile=profile
    )

@app.post("/api/recommend", response_model=RecommendationResponse)
def recommend_endpoint(student: StudentProfile):
    """
    Generates deterministic recommendations, tiers (Safe/Likely/Aspirational),
    curriculum matches, and AI-enriched explanations.
    """
    if student.rank is None:
        raise HTTPException(status_code=400, detail="Student rank is required to generate recommendations.")

    # 1. Deterministic evaluation & preference ranking
    response = generate_recommendations(student)

    # 2. Enrich top recommendations with conversational explanations
    response.preferences = enrich_explanations_with_ai(response.preferences, student)

    return response

# Serve static frontend build if available, otherwise provide API info
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
else:
    @app.get("/")
    def read_root():
        return {
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs"
        }
