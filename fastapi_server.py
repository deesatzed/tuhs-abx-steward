#!/usr/bin/env python3
"""
FastAPI Server for TUHS Antibiotic Steward
Modern, async-native backend with automatic API documentation
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import os
import asyncio
import time

# Optional: load .env locally; harmless in container if not present
try:
    from dotenv import load_dotenv  # ensure python-dotenv is in requirements
    load_dotenv()
except Exception:
    pass

# ✅ FIX: import from the updated file name
# was: from agno_bridge import AgnoBackendBridge
from agno_bridge_v2 import AgnoBackendBridge
from audit_logger import record_audit_entry, get_log_summary

app = FastAPI(
    title="TUHS Antibiotic Steward API",
    description="AI-powered antibiotic recommendation system using Agno agents",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Lazy bridge init (so startup doesn't crash if env missing) ----
_bridge: Optional[AgnoBackendBridge] = None

def get_bridge() -> AgnoBackendBridge:
    global _bridge
    if _bridge is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            # For Fly.io deployment, return a mock bridge that doesn't crash
            print("⚠️  OPENROUTER_API_KEY not set - using mock mode")
            _bridge = MockBridge()  # Create a mock bridge for deployment
        else:
            print("🔧 Initializing Agno Backend Bridge…")
            _bridge = AgnoBackendBridge(api_key)
            print("✅ Agno Bridge ready")
    return _bridge

# Mock bridge for deployment without API key
class MockBridge:
    async def process_request(self, patient_dict):
        return {
            "category": "System",
            "tuhs_recommendation": "System is running but API key not configured. Please set OPENROUTER_API_KEY in Fly.io secrets.",
            "tuhs_confidence": 0.0,
            "final_confidence": 0.0,
            "reputable_sources": [],
            "broader_sources": [],
            "search_decision": {"reasoning": "API key not configured"},
            "search_history": ["System running - configure API key for full functionality"],
            "timestamp": datetime.now().isoformat()
        }

# ---------------------- Models ----------------------
class PatientData(BaseModel):
    age: str = Field(..., description="Patient age")
    gender: str = Field(..., description="Patient gender")
    weight_kg: Optional[str] = Field(None, description="Patient weight in kg")
    gfr: str = Field(..., description="Glomerular filtration rate")
    location: str = Field(..., description="Patient location (Ward/ICU/ED)")
    infection_type: str = Field(..., description="Type of infection")
    allergies: Optional[str] = Field("none", description="Known allergies")
    current_outpt_abx: Optional[str] = Field("none", description="Current outpatient antibiotics")
    current_inp_abx: Optional[str] = Field("none", description="Current inpatient antibiotics")
    culture_results: Optional[str] = Field("Pending", description="Culture results")
    prior_resistance: Optional[str] = Field("", description="Prior resistance patterns")
    source_risk: Optional[str] = Field("", description="Source-specific risk factors")
    inf_risks: Optional[str] = Field("", description="Infection-specific risk factors")

    class Config:
        json_schema_extra = {
            "example": {
                "age": "65",
                "gender": "male",
                "weight_kg": "70",
                "gfr": "80",
                "location": "Ward",
                "infection_type": "pneumonia",
                "allergies": "none",
                "current_outpt_abx": "none",
                "current_inp_abx": "none",
                "culture_results": "Pending",
            }
        }

class RecommendationResponse(BaseModel):
    category: str
    tuhs_recommendation: str
    tuhs_confidence: float
    final_confidence: float
    reputable_sources: list
    broader_sources: list
    search_decision: Dict[str, Any]
    search_history: list
    timestamp: str

# ---------------------- Routes ----------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend"""
    try:
        with open("alpine_frontend.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Frontend not found</h1><p>alpine_frontend.html is missing</p>",
            status_code=404,
        )

@app.get("/health")
async def health_check():
    """Fly HEALTHCHECK hits this."""
    return {
        "status": "healthy",
        "backend": "FastAPI",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }

@app.post("/api/recommendation", response_model=RecommendationResponse)
async def get_recommendation(patient_data: PatientData):
    """Generate antibiotic recommendation based on patient data."""
    # Generate unique request ID
    request_id = f"req_{int(time.time() * 1000)}_{os.urandom(4).hex()}"
    start_time = time.time()

    try:
        bridge = get_bridge()  # may raise RuntimeError if no API key
        patient_dict = patient_data.model_dump()
        print(
            f"📥 [{request_id}] Processing recommendation for {patient_dict.get('age')}yo "
            f"{patient_dict.get('gender')} with {patient_dict.get('infection_type')}"
        )

        result = await bridge.process_request(patient_dict)

        # Make sure required keys exist; add defaults if bridge omits some
        result.setdefault("timestamp", datetime.now().isoformat())
        result.setdefault("reputable_sources", [])
        result.setdefault("broader_sources", [])
        result.setdefault("search_history", [])
        result.setdefault("search_decision", {})

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        print(
            f"✅ [{request_id}] Recommendation generated: {result.get('category')} "
            f"(confidence: {result.get('final_confidence', 0):.0%}) in {duration_ms:.0f}ms"
        )

        # Audit log the successful request
        all_sources = result.get('reputable_sources', []) + result.get('broader_sources', [])
        record_audit_entry(
            request_id=request_id,
            input_data=patient_dict,
            recommendation=result.get('tuhs_recommendation', ''),
            category=result.get('category'),
            tuhs_confidence=result.get('tuhs_confidence'),
            final_confidence=result.get('final_confidence'),
            sources=all_sources,
            duration_ms=duration_ms,
            status="success",
        )

        return JSONResponse(content=result)

    except RuntimeError as e:
        # Configuration problems (like missing OPENROUTER_API_KEY)
        duration_ms = (time.time() - start_time) * 1000

        # Audit log the error
        record_audit_entry(
            request_id=request_id,
            input_data=patient_data.model_dump(),
            duration_ms=duration_ms,
            status="error",
            error=f"Configuration error: {str(e)}",
        )

        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()

        duration_ms = (time.time() - start_time) * 1000

        # Audit log the error
        record_audit_entry(
            request_id=request_id,
            input_data=patient_data.model_dump(),
            duration_ms=duration_ms,
            status="error",
            error=f"Processing error: {str(e)}",
        )

        raise HTTPException(status_code=500, detail=f"Error generating recommendation: {e}") from e

@app.get("/api/models")
async def list_models():
    default_model = os.getenv("DEFAULT_MODEL", "google/gemini-2.5-flash-lite-preview-09-2025")
    fallback_model = os.getenv("FALLBACK_MODEL", "x-ai/grok-4-fast")
    complex_model = os.getenv("COMPLEX_MODEL", "qwen/qwen3-max")
    icu_model = os.getenv("ICU_MODEL", "x-ai/grok-4-fast")
    return {
        "current_model": default_model,
        "available_models": [
            default_model,
            fallback_model,
            complex_model,
            icu_model,
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ],
        "model_routing": {
            "default": default_model,
            "fallback": fallback_model,
            "complex_cases": complex_model,
            "icu_cases": icu_model,
        },
    }

@app.get("/api/audit/summary")
async def get_audit_summary(date: Optional[str] = None):
    """Get audit log summary for a specific date (defaults to today)"""
    try:
        if date:
            # Parse date string (YYYY-MM-DD format)
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = None

        summary = get_log_summary(date=target_date)
        return summary

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit summary: {e}") from e

class EvidenceSearchRequest(BaseModel):
    query: str
    infection_type: str
    tuhs_recommendation: str
    tuhs_confidence: float

@app.post("/api/search-evidence")
async def search_evidence(request: EvidenceSearchRequest):
    """Manual evidence search across reputable sources."""
    try:
        from evidence_coordinator_full import FullEvidenceCoordinator
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            # Return mock response for deployment without API key
            return {
                "reputable_sources": [],
                "broader_sources": [],
                "final_confidence": 0.0,
                "search_history": ["Evidence search requires API key configuration"]
            }
        coordinator = FullEvidenceCoordinator(api_key)
        search_result = await coordinator.search_sequential(
            query=request.query,
            tuhs_confidence=0.5,  # force search
            tuhs_response=request.tuhs_recommendation,
        )
        return {
            "reputable_sources": [
                {
                    "source": s.source_name,
                    "title": s.title,
                    "url": s.url,
                    "finding": s.key_finding,
                }
                for s in (search_result.reputable_sources or [])
            ],
            "broader_sources": [
                {
                    "source": s.source_name,
                    "title": s.title,
                    "url": s.url,
                    "finding": s.key_finding,
                }
                for s in (search_result.broader_sources or [])
            ],
            "final_confidence": search_result.final_confidence,
            "search_history": search_result.search_history,
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Evidence search failed: {e}") from e

@app.on_event("startup")
async def startup_event():
    print("🚀 TUHS Antibiotic Steward - FastAPI Server")
    print("=" * 50)
    print("📡 API Docs:     /api/docs")
    print("🌐 Frontend:     /")
    print("❤️  Health:      /health")
    print("=" * 50)

if __name__ == "__main__":
    # Dev-only. In containers, use Dockerfile CMD (uvicorn) without reload.
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    reload_flag = os.getenv("DEBUG", "0") == "1"
    uvicorn.run("fastapi_server:app", host="0.0.0.0", port=port, proxy_headers=True, reload=reload_flag)
