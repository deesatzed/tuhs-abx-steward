"""
Feedback Collection System
Collects clinical feedback on recommendations for continuous learning
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import uuid
from pathlib import Path

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class PatientCase(BaseModel):
    age: str
    gender: str
    infection_type: str
    allergies: str
    gfr: str
    location: str
    inf_risks: Optional[str] = None
    source_risk: Optional[str] = None

class FeedbackSubmission(BaseModel):
    recommendation_id: Optional[str] = None
    patient_case: PatientCase
    actual_recommendation: str
    feedback_type: str
    expected_recommendation: str
    reasoning: str
    outcome: Optional[str] = None
    submitted_by: str
    supporting_evidence: Optional[List[str]] = None

class FeedbackStore:
    """Store feedback in JSON file"""

    def __init__(self, file_path: str = "feedback_log.json"):
        self.file_path = Path(file_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create feedback log file if it doesn't exist"""
        if not self.file_path.exists():
            with open(self.file_path, 'w') as f:
                json.dump({"feedback": [], "stats": {"total": 0, "pending": 0, "approved": 0, "rejected": 0}}, f, indent=2)

    def save_feedback(self, feedback: dict) -> str:
        """Save feedback and return feedback ID"""
        feedback_id = f"fb-{uuid.uuid4().hex[:8]}"
        feedback["feedback_id"] = feedback_id
        feedback["submitted_at"] = datetime.utcnow().isoformat()
        feedback["review_status"] = "pending"
        feedback["priority"] = self._calculate_priority(feedback)

        # Load existing feedback
        with open(self.file_path, 'r') as f:
            feedback_log = json.load(f)

        # Append new feedback
        feedback_log["feedback"].append(feedback)
        feedback_log["stats"]["total"] += 1
        feedback_log["stats"]["pending"] += 1

        # Save
        with open(self.file_path, 'w') as f:
            json.dump(feedback_log, f, indent=2)

        print(f"✅ Feedback saved: {feedback_id}")
        print(f"   Type: {feedback['feedback_type']}")
        print(f"   Priority: {feedback['priority']}")

        return feedback_id

    def _calculate_priority(self, feedback: dict) -> str:
        """Calculate priority based on feedback type"""
        critical_types = ["incorrect_drug", "contraindication_missed", "allergy_misclassification"]

        if feedback["feedback_type"] in critical_types:
            return "critical"
        elif feedback["feedback_type"] in ["missing_drug", "incorrect_route"]:
            return "high"
        else:
            return "medium"

    def get_pending_feedback(self, priority: Optional[str] = None) -> List[dict]:
        """Get pending feedback, optionally filtered by priority"""
        with open(self.file_path, 'r') as f:
            feedback_log = json.load(f)

        pending = [
            fb for fb in feedback_log["feedback"]
            if fb["review_status"] == "pending"
        ]

        if priority:
            pending = [fb for fb in pending if fb["priority"] == priority]

        return pending

    def get_feedback_by_id(self, feedback_id: str) -> Optional[dict]:
        """Get specific feedback by ID"""
        with open(self.file_path, 'r') as f:
            feedback_log = json.load(f)

        for fb in feedback_log["feedback"]:
            if fb["feedback_id"] == feedback_id:
                return fb

        return None

    def update_feedback_status(self, feedback_id: str, status: str, updated_by: str, reason: str):
        """Update feedback review status"""
        with open(self.file_path, 'r') as f:
            feedback_log = json.load(f)

        for fb in feedback_log["feedback"]:
            if fb["feedback_id"] == feedback_id:
                old_status = fb["review_status"]
                fb["review_status"] = status
                fb["reviewed_at"] = datetime.utcnow().isoformat()
                fb["reviewed_by"] = updated_by
                fb["review_reason"] = reason

                # Update stats
                if old_status == "pending":
                    feedback_log["stats"]["pending"] -= 1
                if status == "approved":
                    feedback_log["stats"]["approved"] += 1
                elif status == "rejected":
                    feedback_log["stats"]["rejected"] += 1

                break

        with open(self.file_path, 'w') as f:
            json.dump(feedback_log, f, indent=2)

    def get_stats(self) -> dict:
        """Get feedback statistics"""
        with open(self.file_path, 'r') as f:
            feedback_log = json.load(f)
        return feedback_log["stats"]

feedback_store = FeedbackStore()

@router.post("/", summary="Submit feedback on a recommendation")
async def submit_feedback(feedback: FeedbackSubmission):
    """
    Submit feedback on an antibiotic recommendation

    Feedback types:
    - incorrect_drug: Wrong antibiotic selected
    - missing_drug: Should have included additional drug
    - incorrect_route: Wrong route (IV vs PO)
    - allergy_misclassification: Allergy severity wrong
    - dosing_error: Wrong dose
    - contraindication_missed: Missed a contraindication
    - success_confirmation: Positive feedback (correct recommendation)
    """
    feedback_id = feedback_store.save_feedback(feedback.dict())

    return {
        "feedback_id": feedback_id,
        "status": "submitted",
        "message": "Thank you for your feedback. A builder will review this.",
        "priority": feedback_store.get_feedback_by_id(feedback_id)["priority"]
    }

@router.get("/pending", summary="Get pending feedback (public)")
async def get_pending_feedback(priority: Optional[str] = None):
    """
    Get all pending feedback

    Query params:
    - priority: Filter by priority (critical, high, medium)
    """
    pending = feedback_store.get_pending_feedback(priority)

    # Return simplified view (hide sensitive builder info)
    return {
        "count": len(pending),
        "pending_feedback": [
            {
                "feedback_id": fb["feedback_id"],
                "submitted_at": fb["submitted_at"],
                "feedback_type": fb["feedback_type"],
                "priority": fb["priority"],
                "case_summary": f"{fb['patient_case']['age']}yo {fb['patient_case']['gender']}, {fb['patient_case']['infection_type']}"
            }
            for fb in pending
        ]
    }

@router.get("/{feedback_id}", summary="Get specific feedback details")
async def get_feedback_details(feedback_id: str):
    """Get detailed information about specific feedback"""
    feedback = feedback_store.get_feedback_by_id(feedback_id)

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return feedback

@router.get("/stats/summary", summary="Get feedback statistics")
async def get_feedback_stats():
    """Get overall feedback statistics"""
    return feedback_store.get_stats()
