#!/usr/bin/env python3
"""
FastAPI Server for TUHS Antibiotic Steward
Modern, async-native backend with automatic API documentation
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import os
import asyncio
import time
import json
import uuid

# Optional: load .env locally; harmless in container if not present
try:
    from dotenv import load_dotenv  # ensure python-dotenv is in requirements
    load_dotenv()
except Exception:
    pass

# ✅ V3 Architecture: Using modular guideline system
from lib.recommendation_engine import RecommendationEngine
from audit_logger import record_audit_entry, get_log_summary

app = FastAPI(
    title="TUHS Antibiotic Steward API",
    description="AI-powered antibiotic recommendation system using v3 modular architecture",
    version="3.0.0",
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

# Error report storage directory
ERROR_REPORTS_DIR = Path("logs/error_reports")
ERROR_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---- V3 Engine Initialization ----
_engine: Optional[RecommendationEngine] = None

def get_engine() -> RecommendationEngine:
    """Lazy initialization of v3 recommendation engine"""
    global _engine
    if _engine is None:
        print("🔧 Initializing v3 Recommendation Engine...")
        try:
            _engine = RecommendationEngine()
            print("✅ v3 Engine ready (using modular JSON guidelines)")
        except Exception as e:
            print(f"❌ Failed to initialize v3 engine: {e}")
            raise RuntimeError(f"Failed to initialize recommendation engine: {e}")
    return _engine

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
        "backend": "FastAPI v3",
        "version": "3.0.0",
        "architecture": "modular_json_guidelines",
        "timestamp": datetime.now().isoformat(),
    }

@app.post("/api/recommendation")
async def get_recommendation(patient_data: PatientData):
    """Generate antibiotic recommendation using v3 modular architecture."""
    # Generate unique request ID
    request_id = f"req_{int(time.time() * 1000)}_{os.urandom(4).hex()}"
    start_time = time.time()

    try:
        engine = get_engine()
        patient_dict = patient_data.model_dump()

        print(
            f"📥 [{request_id}] Processing v3 recommendation for {patient_dict.get('age')}yo "
            f"{patient_dict.get('gender')} with {patient_dict.get('infection_type')}"
        )

        # Convert FastAPI model to v3 engine format
        # Handle empty strings from frontend
        def safe_int(value, default=0):
            try:
                return int(value) if value and str(value).strip() else default
            except (ValueError, TypeError):
                return default

        def safe_float(value, default=70.0):
            try:
                return float(value) if value and str(value).strip() else default
            except (ValueError, TypeError):
                return default

        age = safe_int(patient_dict.get('age'), None)
        infection_type = patient_dict.get('infection_type', '').lower().replace(' ', '_').replace('/', '_')

        # Validate required fields
        if not age or age == 0:
            raise HTTPException(status_code=400, detail="Age is required")
        if not infection_type or infection_type == '':
            raise HTTPException(status_code=400, detail="Infection type is required")

        v3_input = {
            'age': age,
            'infection_type': infection_type,
            'allergies': patient_dict.get('allergies', 'none'),
            'weight': safe_float(patient_dict.get('weight_kg'), 70),
            'crcl': safe_float(patient_dict.get('gfr'), 100),  # Using GFR as proxy for CrCl
            'fever': 'fever' in patient_dict.get('inf_risks', '').lower() or 'fever' in patient_dict.get('infection_type', '').lower(),
            'severity': 'icu' if patient_dict.get('location', '').lower() == 'icu' else 'moderate',
            'pregnancy': 'pregnan' in patient_dict.get('inf_risks', '').lower(),
        }

        # Call v3 engine (synchronous)
        result = engine.get_recommendation(v3_input)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        if result['success']:
            print(
                f"✅ [{request_id}] v3 Recommendation: {result.get('infection_category')} "
                f"({len(result.get('drugs', []))} drugs) in {duration_ms:.0f}ms"
            )

            # Convert v3 format to FastAPI response format
            response = {
                "category": result.get('infection_category', 'Unknown'),
                "tuhs_recommendation": result.get('recommendation', ''),
                "tuhs_confidence": 1.0,  # v3 uses rule-based, not confidence scoring
                "final_confidence": 1.0,
                "reputable_sources": [],  # v3 doesn't use external sources
                "broader_sources": [],
                "search_decision": {"reasoning": "v3 modular architecture uses local JSON guidelines"},
                "search_history": result.get('warnings', []),
                "timestamp": datetime.now().isoformat(),
                "drugs": result.get('drugs', []),
                "warnings": result.get('warnings', []),
                "monitoring": result.get('monitoring', []),
                "rationale": result.get('rationale', ''),
                "metadata": result.get('metadata', {})
            }

            # Audit log
            record_audit_entry(
                request_id=request_id,
                input_data=patient_dict,
                recommendation=result.get('recommendation', ''),
                category=result.get('infection_category'),
                tuhs_confidence=1.0,
                final_confidence=1.0,
                sources=[],
                duration_ms=duration_ms,
                status="success",
            )

            return JSONResponse(content=response)
        else:
            # v3 returned errors
            errors = result.get('errors', ['Unknown error'])
            print(f"❌ [{request_id}] v3 Errors: {errors}")

            record_audit_entry(
                request_id=request_id,
                input_data=patient_dict,
                duration_ms=duration_ms,
                status="error",
                error=f"v3 engine errors: {', '.join(errors)}",
            )

            raise HTTPException(status_code=400, detail=f"Recommendation errors: {', '.join(errors)}")

    except RuntimeError as e:
        duration_ms = (time.time() - start_time) * 1000
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

class ErrorReport(BaseModel):
    error_type: str = Field(..., description="Type of error: contraindicated|wrong_drug|wrong_dose|missed_allergy|missed_interaction|wrong_route|other")
    severity: str = Field(..., description="Severity: low|medium|high|critical")
    error_description: str = Field(..., description="Description of the error")
    expected_recommendation: str = Field(..., description="What should have been recommended")
    reporter_name: Optional[str] = Field(None, description="Name or ID of reporter (optional)")
    patient_data: Dict[str, Any] = Field(..., description="De-identified patient data")
    recommendation_given: Dict[str, Any] = Field(..., description="The recommendation that was given")

    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "contraindicated",
                "severity": "high",
                "error_description": "System gave ceftriaxone to patient with severe PCN allergy (anaphylaxis)",
                "expected_recommendation": "Should have given aztreonam instead",
                "reporter_name": "Dr. Smith",
                "patient_data": {
                    "age": 55,
                    "infection_type": "uti",
                    "fever": True,
                    "allergies": "Penicillin (anaphylaxis)"
                },
                "recommendation_given": {
                    "drugs": ["Ceftriaxone"],
                    "route": "IV"
                }
            }
        }

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

@app.post("/api/error-report")
async def submit_error_report(error_report: ErrorReport):
    """
    Submit an error report from a pilot user (pharmacist)
    """
    try:
        # Generate unique error ID
        error_id = f"ERR-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

        # Convert to dict and add metadata
        report_dict = error_report.model_dump()
        report_dict['error_id'] = error_id
        report_dict['status'] = 'new'
        report_dict['created_at'] = datetime.now().isoformat()

        # Validate severity
        valid_severities = ['low', 'medium', 'high', 'critical']
        if report_dict['severity'] not in valid_severities:
            raise ValueError(f"Invalid severity. Must be one of: {valid_severities}")

        # Validate error_type
        valid_types = ['contraindicated', 'wrong_drug', 'wrong_dose', 'missed_allergy',
                       'missed_interaction', 'wrong_route', 'other']
        if report_dict['error_type'] not in valid_types:
            raise ValueError(f"Invalid error_type. Must be one of: {valid_types}")

        # Save to JSONL file (one report per line)
        today = datetime.now().strftime('%Y-%m-%d')
        report_file = ERROR_REPORTS_DIR / f"{today}.jsonl"

        with open(report_file, 'a') as f:
            f.write(json.dumps(report_dict) + '\n')

        print(f"📝 Error report submitted: {error_id} (severity: {report_dict['severity']})")

        # Log critical errors prominently
        if report_dict.get('severity') == 'critical':
            print(f"🚨 CRITICAL ERROR REPORT: {error_id}")
            print(f"   Description: {report_dict['error_description'][:100]}")

        return {
            "success": True,
            "error_id": error_id,
            "message": "Error report submitted successfully. Thank you for helping improve the system."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        print(f"❌ Failed to save error report: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving report: {e}") from e


@app.get("/api/error-reports")
async def get_error_reports(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: Optional[int] = 50
):
    """
    Retrieve error reports (for admin dashboard)

    Query Parameters:
    - status: Filter by status (new, verified, in_progress, fixed, closed)
    - severity: Filter by severity (low, medium, high, critical)
    - limit: Maximum number of reports to return (default: 50)
    """
    try:
        all_reports = []

        # Read all JSONL files (most recent first)
        report_files = sorted(ERROR_REPORTS_DIR.glob("*.jsonl"), reverse=True)

        for report_file in report_files:
            with open(report_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    report = json.loads(line)

                    # Filter by status if provided
                    if status and report.get('status') != status:
                        continue

                    # Filter by severity if provided
                    if severity and report.get('severity') != severity:
                        continue

                    all_reports.append(report)

                    # Stop if we've hit the limit
                    if len(all_reports) >= limit:
                        break

            if len(all_reports) >= limit:
                break

        # Sort by timestamp (newest first)
        all_reports.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # Apply limit
        all_reports = all_reports[:limit]

        # Calculate summary stats
        stats = {
            'total': len(all_reports),
            'by_status': {},
            'by_severity': {},
            'by_type': {}
        }

        for report in all_reports:
            status_val = report.get('status', 'unknown')
            severity_val = report.get('severity', 'unknown')
            type_val = report.get('error_type', 'unknown')

            stats['by_status'][status_val] = stats['by_status'].get(status_val, 0) + 1
            stats['by_severity'][severity_val] = stats['by_severity'].get(severity_val, 0) + 1
            stats['by_type'][type_val] = stats['by_type'].get(type_val, 0) + 1

        return {
            "success": True,
            "count": len(all_reports),
            "reports": all_reports,
            "stats": stats
        }

    except Exception as e:
        print(f"❌ Failed to retrieve error reports: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving reports: {e}") from e


@app.patch("/api/error-report/{error_id}/status")
async def update_error_status(error_id: str, new_status: str):
    """
    Update error report status

    Valid statuses: new, verified, in_progress, fixed, closed, wont_fix, not_reproduced
    """
    try:
        valid_statuses = ['new', 'verified', 'in_progress', 'fixed', 'closed', 'wont_fix', 'not_reproduced']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        # Find and update the error report
        updated = False
        for report_file in ERROR_REPORTS_DIR.glob("*.jsonl"):
            reports = []
            with open(report_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    report = json.loads(line)
                    if report['error_id'] == error_id:
                        old_status = report.get('status')
                        report['status'] = new_status
                        report['status_updated_at'] = datetime.now().isoformat()
                        updated = True
                        print(f"📝 Updated {error_id}: {old_status} → {new_status}")
                    reports.append(report)

            # Rewrite file with updated report
            if updated:
                with open(report_file, 'w') as f:
                    for report in reports:
                        f.write(json.dumps(report) + '\n')
                break

        if not updated:
            raise HTTPException(status_code=404, detail=f"Error report {error_id} not found")

        return {
            "success": True,
            "message": f"Error {error_id} status updated to {new_status}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to update error status: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating status: {e}") from e


@app.on_event("startup")
async def startup_event():
    print("🚀 TUHS Antibiotic Steward - FastAPI Server")
    print("=" * 50)
    print("📡 API Docs:     /api/docs")
    print("🌐 Frontend:     /")
    print("❤️  Health:      /health")
    print("📝 Error Reports: /api/error-reports")
    print("=" * 50)

if __name__ == "__main__":
    # Dev-only. In containers, use Dockerfile CMD (uvicorn) without reload.
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    reload_flag = os.getenv("DEBUG", "0") == "1"
    uvicorn.run("fastapi_server:app", host="0.0.0.0", port=port, proxy_headers=True, reload=reload_flag)
