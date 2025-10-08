# Ongoing Learning System Design
## TUHS Antibiotic Steward - Continuous Improvement via Guideline Updates

---

## Overview

The learning system allows clinical experts to provide feedback on recommendations, which can then be reviewed and approved by authenticated "builders" to update the institutional guidelines (JSON files). This creates a continuous improvement loop where the system learns from real-world usage.

---

## Architecture

```
┌─────────────────┐
│  Clinical User  │
│   Reviews Rec   │
└────────┬────────┘
         │ Submits Feedback
         ↓
┌─────────────────────────┐
│   Feedback Collection   │
│   feedback_log.json     │
└────────┬────────────────┘
         │
         ↓
┌──────────────────────────┐
│  Authenticated Builder   │
│  Reviews + Approves      │
└────────┬─────────────────┘
         │ Approves Update
         ↓
┌──────────────────────────┐
│  Guideline Updater       │
│  Updates JSON + Git      │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│  Version Control         │
│  Git commit with audit   │
└──────────────────────────┘
```

---

## Components

### 1. Feedback Collection API

**Endpoint:** `POST /api/feedback`

**Purpose:** Allow clinical users to submit feedback on recommendations

**Input Schema:**
```json
{
  "recommendation_id": "uuid-from-audit-log",
  "patient_case": {
    "age": "55",
    "gender": "male",
    "infection_type": "intra_abdominal",
    "allergies": "Penicillin (rash)",
    "gfr": "66"
  },
  "actual_recommendation": "Aztreonam + Metronidazole",
  "feedback_type": "incorrect_drug",
  "expected_recommendation": "Piperacillin-tazobactam + Metronidazole",
  "reasoning": "Mild PCN allergy (rash only) should allow piperacillin use. Patient did well on pip-tazo.",
  "outcome": "Patient completed treatment successfully with pip-tazo",
  "submitted_by": "Dr. Smith (ID Physician)",
  "submitted_at": "2025-10-07T10:00:00Z"
}
```

**Feedback Types:**
- `incorrect_drug` - Wrong antibiotic selected
- `missing_drug` - Should have included additional drug
- `incorrect_route` - Wrong route (IV vs PO)
- `allergy_misclassification` - Allergy severity wrong
- `dosing_error` - Wrong dose (for future Step 2)
- `contraindication_missed` - Missed a contraindication
- `success_confirmation` - Positive feedback (rec was correct)

---

### 2. Feedback Review Dashboard

**Endpoint:** `GET /api/admin/feedback/pending`

**Purpose:** Authenticated builders review pending feedback

**Authentication:** JWT token with `builder` role

**Output:**
```json
{
  "pending_feedback": [
    {
      "feedback_id": "fb-123",
      "submitted_at": "2025-10-07T10:00:00Z",
      "submitted_by": "Dr. Smith",
      "case_summary": "55yo male, intra-abdominal, PCN rash",
      "issue": "Aztreonam given instead of Piperacillin-tazobactam",
      "suggested_fix": {
        "guideline_section": "Intra-Abdominal",
        "allergy_classification": "Clarify mild vs severe PCN allergy",
        "proposed_json_change": {
          "file": "agno_bridge_v2.py",
          "section": "allergy_handling",
          "change_type": "instruction_clarification"
        }
      },
      "evidence": [
        "Patient outcome: Successful",
        "Supporting literature: IDSA guidelines on mild PCN allergy"
      ],
      "review_status": "pending",
      "priority": "high"
    }
  ]
}
```

---

### 3. Approval & Update System

**Endpoint:** `POST /api/admin/feedback/{feedback_id}/approve`

**Purpose:** Builder approves feedback and triggers guideline update

**Input:**
```json
{
  "approved": true,
  "update_type": "instruction_modification",
  "target_file": "agno_bridge_v2.py",
  "change_description": "Add explicit mild PCN allergy handling",
  "git_commit_message": "Fix: Clarify mild vs severe PCN allergy classification",
  "approved_by": "Builder John Doe",
  "approval_reason": "Consistent with IDSA guidelines and patient outcomes"
}
```

**Actions Triggered:**
1. Create git branch: `guideline-update-{feedback_id}`
2. Apply JSON/code changes
3. Run automated tests
4. Create git commit with audit trail
5. (Optional) Create pull request for peer review
6. Merge to main
7. Trigger server reload

---

### 4. JSON Update Mechanism

**Approach 1: Instruction Modifications** (Code-based)
- Updates to `agno_bridge_v2.py` instruction generation
- Example: Clarifying allergy classification
- Requires code deployment

**Approach 2: Guideline JSON Modifications** (Data-based)
- Updates to `ABX_Selection.json` or `ABX_Dosing.json`
- Example: Adding new drug regimen
- No code deployment needed (hot reload)

**JSON Patch Format:**
```json
{
  "file": "ABX_Selection.json",
  "path": "infection_guidelines[0].sub_sections[1].empiric_regimens",
  "operation": "add",
  "value": {
    "pcp_allergy_status": "MILD Penicillin Allergy (rash only)",
    "regimen": [
      "Piperacillin-tazobactam IV",
      "Metronidazole IV"
    ],
    "notes": "Added 2025-10-07 based on feedback fb-123"
  }
}
```

---

### 5. Version Control & Audit Trail

Every guideline change is tracked with:

**Git Commit Format:**
```
fix: Clarify mild vs severe PCN allergy classification

Feedback: fb-123
Submitted by: Dr. Smith (ID Physician)
Approved by: Builder John Doe
Date: 2025-10-07

Issue: System treating mild PCN allergy (rash) as severe
Expected: Allow piperacillin for mild rash
Evidence: 3 patient cases, IDSA guidelines

Changes:
- Updated allergy_handling instructions in agno_bridge_v2.py
- Added explicit mild vs severe classification
- Added example for intra-abdominal infection

Testing:
- pytest tests/test_drug_selection_allergy.py PASSED
- Manual test: Mild rash → Pip-tazo ✅
- Manual test: Anaphylaxis → Aztreonam ✅
```

**Audit Log Entry:**
```json
{
  "change_id": "ch-456",
  "feedback_id": "fb-123",
  "timestamp": "2025-10-07T11:00:00Z",
  "change_type": "instruction_modification",
  "files_modified": ["agno_bridge_v2.py"],
  "approved_by": "Builder John Doe",
  "git_commit": "a1b2c3d4",
  "rollback_commit": "d4c3b2a1",
  "validation_tests_passed": true,
  "deployed_at": "2025-10-07T11:05:00Z"
}
```

---

## Implementation Files

### File 1: `feedback_collector.py`

```python
"""
Feedback Collection System
Collects clinical feedback on recommendations
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import uuid

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class FeedbackSubmission(BaseModel):
    recommendation_id: str
    patient_case: dict
    actual_recommendation: str
    feedback_type: str
    expected_recommendation: str
    reasoning: str
    outcome: Optional[str] = None
    submitted_by: str

class FeedbackStore:
    """Store feedback in JSON file"""

    def __init__(self, file_path: str = "feedback_log.json"):
        self.file_path = file_path

    def save_feedback(self, feedback: dict) -> str:
        """Save feedback and return feedback ID"""
        feedback_id = f"fb-{uuid.uuid4().hex[:8]}"
        feedback["feedback_id"] = feedback_id
        feedback["submitted_at"] = datetime.utcnow().isoformat()
        feedback["review_status"] = "pending"

        # Load existing feedback
        try:
            with open(self.file_path, 'r') as f:
                feedback_log = json.load(f)
        except FileNotFoundError:
            feedback_log = {"feedback": []}

        # Append new feedback
        feedback_log["feedback"].append(feedback)

        # Save
        with open(self.file_path, 'w') as f:
            json.dump(feedback_log, f, indent=2)

        return feedback_id

feedback_store = FeedbackStore()

@router.post("/")
async def submit_feedback(feedback: FeedbackSubmission):
    """Submit feedback on a recommendation"""
    feedback_id = feedback_store.save_feedback(feedback.dict())

    return {
        "feedback_id": feedback_id,
        "status": "submitted",
        "message": "Thank you for your feedback. A builder will review this."
    }

@router.get("/pending")
async def get_pending_feedback():
    """Get all pending feedback (builder only)"""
    # TODO: Add authentication check

    try:
        with open("feedback_log.json", 'r') as f:
            feedback_log = json.load(f)
    except FileNotFoundError:
        return {"pending_feedback": []}

    pending = [
        fb for fb in feedback_log["feedback"]
        if fb["review_status"] == "pending"
    ]

    return {"pending_feedback": pending}
```

---

### File 2: `guideline_updater.py`

```python
"""
Guideline Update System
Applies approved changes to guidelines with version control
"""
import json
import subprocess
from datetime import datetime
from typing import Dict, Any

class GuidelineUpdater:
    """Manages guideline updates with git version control"""

    def __init__(self):
        self.selection_file = "ABX_Selection.json"
        self.dosing_file = "ABX_Dosing.json"
        self.audit_file = "guideline_changes.log"

    def apply_json_patch(self, file_path: str, patch: Dict[str, Any]) -> bool:
        """Apply a JSON patch to a guideline file"""
        try:
            # Load current JSON
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Apply patch (simplified - use jsonpatch library for production)
            if patch["operation"] == "add":
                # Navigate to path and add value
                self._apply_add_operation(data, patch["path"], patch["value"])
            elif patch["operation"] == "modify":
                self._apply_modify_operation(data, patch["path"], patch["value"])

            # Save updated JSON
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error applying patch: {e}")
            return False

    def commit_changes(self, feedback_id: str, approved_by: str, message: str):
        """Commit changes to git with audit trail"""
        commit_message = f"""Update guidelines based on feedback {feedback_id}

Approved by: {approved_by}
Date: {datetime.utcnow().isoformat()}

{message}
"""

        try:
            # Git add
            subprocess.run(["git", "add", "."], check=True)

            # Git commit
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True
            )

            # Log change
            self._log_change(feedback_id, approved_by, message)

            return True
        except subprocess.CalledProcessError as e:
            print(f"Git commit failed: {e}")
            return False

    def _log_change(self, feedback_id: str, approved_by: str, message: str):
        """Log change to audit file"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "feedback_id": feedback_id,
            "approved_by": approved_by,
            "message": message
        }

        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

    def _apply_add_operation(self, data: dict, path: str, value: Any):
        """Navigate JSON path and add value"""
        # Simplified implementation
        # For production, use jsonpatch library
        pass

    def _apply_modify_operation(self, data: dict, path: str, value: Any):
        """Navigate JSON path and modify value"""
        # Simplified implementation
        pass

updater = GuidelineUpdater()
```

---

### File 3: `builder_api.py`

```python
"""
Builder API
Authenticated endpoints for builders to review and approve feedback
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter(prefix="/api/admin", tags=["admin"])

class ApprovalRequest(BaseModel):
    approved: bool
    update_type: str
    change_description: str
    git_commit_message: str
    approval_reason: str

# Simple authentication (replace with proper JWT in production)
def verify_builder_token(authorization: str = Header(None)):
    """Verify builder authentication token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    # TODO: Verify JWT token
    # For now, just check if token exists
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"role": "builder", "username": "Builder"}

@router.post("/feedback/{feedback_id}/approve")
async def approve_feedback(
    feedback_id: str,
    approval: ApprovalRequest,
    builder: dict = Depends(verify_builder_token)
):
    """Approve feedback and trigger guideline update"""

    # Load feedback
    try:
        with open("feedback_log.json", 'r') as f:
            feedback_log = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Find feedback
    feedback = None
    for fb in feedback_log["feedback"]:
        if fb["feedback_id"] == feedback_id:
            feedback = fb
            break

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if not approval.approved:
        # Mark as rejected
        feedback["review_status"] = "rejected"
        feedback["rejected_by"] = builder["username"]
        feedback["rejection_reason"] = approval.approval_reason
    else:
        # Mark as approved
        feedback["review_status"] = "approved"
        feedback["approved_by"] = builder["username"]
        feedback["approval_reason"] = approval.approval_reason

        # Trigger guideline update
        from guideline_updater import updater
        success = updater.commit_changes(
            feedback_id,
            builder["username"],
            approval.git_commit_message
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update guidelines")

    # Save updated feedback log
    with open("feedback_log.json", 'w') as f:
        json.dump(feedback_log, f, indent=2)

    return {
        "feedback_id": feedback_id,
        "status": "approved" if approval.approved else "rejected",
        "message": "Guidelines will be updated" if approval.approved else "Feedback rejected"
    }

@router.get("/feedback/stats")
async def get_feedback_stats(builder: dict = Depends(verify_builder_token)):
    """Get feedback statistics"""

    try:
        with open("feedback_log.json", 'r') as f:
            feedback_log = json.load(f)
    except FileNotFoundError:
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

    total = len(feedback_log["feedback"])
    pending = sum(1 for fb in feedback_log["feedback"] if fb["review_status"] == "pending")
    approved = sum(1 for fb in feedback_log["feedback"] if fb["review_status"] == "approved")
    rejected = sum(1 for fb in feedback_log["feedback"] if fb["review_status"] == "rejected")

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }
```

---

## Integration with FastAPI Server

Add to `fastapi_server.py`:

```python
# Import feedback routers
from feedback_collector import router as feedback_router
from builder_api import router as builder_router

# Register routers
app.include_router(feedback_router)
app.include_router(builder_router)
```

---

## User Workflows

### Clinical Expert Workflow:

1. **Review Recommendation**
   - Patient case: 55yo male, intra-abdominal, PCN rash
   - System recommended: Aztreonam + Metronidazole
   - Expert thinks: Should be Piperacillin-tazobactam

2. **Submit Feedback**
   ```bash
   POST /api/feedback
   {
     "feedback_type": "incorrect_drug",
     "expected_recommendation": "Piperacillin-tazobactam + Metronidazole",
     "reasoning": "Mild PCN allergy (rash only) should allow pip-tazo",
     "outcome": "Patient did well on pip-tazo"
   }
   ```

3. **Receive Confirmation**
   - Feedback ID: fb-12345678
   - Status: Pending review by builder

---

### Builder Workflow:

1. **View Pending Feedback**
   ```bash
   GET /api/admin/feedback/pending
   Authorization: Bearer {jwt-token}
   ```

2. **Review Evidence**
   - Patient outcome
   - Supporting literature
   - Similar cases
   - Current guideline text

3. **Approve Update**
   ```bash
   POST /api/admin/feedback/fb-12345678/approve
   {
     "approved": true,
     "update_type": "instruction_modification",
     "change_description": "Clarify mild vs severe PCN allergy",
     "git_commit_message": "Fix: Allow pip-tazo for mild PCN rash",
     "approval_reason": "Consistent with IDSA guidelines"
   }
   ```

4. **System Automatically**:
   - Updates code/JSON
   - Runs tests
   - Creates git commit
   - Reloads guidelines
   - Notifies expert

---

## Security Considerations

1. **Authentication**: JWT tokens with `builder` role
2. **Audit Trail**: Every change logged with approver identity
3. **Git History**: Full version control with rollback capability
4. **Test Validation**: Changes must pass pytest before deployment
5. **Peer Review**: Optional PR review before merging to main

---

## Metrics & Monitoring

Track:
- **Feedback Rate**: Submissions per 100 recommendations
- **Approval Rate**: % of feedback approved
- **Time to Resolution**: Days from submission to approval
- **Impact**: Before/after accuracy comparison
- **Top Issues**: Most common feedback types

---

## Future Enhancements

1. **Machine Learning Integration**
   - Analyze feedback patterns
   - Suggest guideline updates automatically
   - Predict which cases need expert review

2. **Collaborative Review**
   - Multiple builders vote on changes
   - Consensus-based approval

3. **A/B Testing**
   - Deploy changes to subset of users
   - Measure impact before full rollout

4. **Natural Language Updates**
   - Builders describe changes in plain English
   - AI generates JSON patches automatically

---

## Implementation Priority

**Phase 1 (Immediate):**
- [x] Fix mild vs severe PCN allergy classification (DONE)
- [ ] Basic feedback collection API
- [ ] Simple approval workflow

**Phase 2 (Next 2 weeks):**
- [ ] Authentication system
- [ ] Git integration
- [ ] Audit trail

**Phase 3 (Next month):**
- [ ] Builder dashboard UI
- [ ] Automated testing on updates
- [ ] Metrics & reporting

**Phase 4 (Future):**
- [ ] ML-powered suggestions
- [ ] A/B testing framework
- [ ] Natural language updates
