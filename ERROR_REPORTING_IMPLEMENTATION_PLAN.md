# Error Reporting & Feedback Loop Implementation Plan

**Created**: 2025-10-08
**Purpose**: Enable pilot pharmacists to flag errors and create automated verification/fix cycle
**Status**: Phase 1 - In Progress

---

## Architecture Overview

```
Pharmacist UI → Error Report Modal → Backend API → JSONL Storage
                                                         ↓
                                            Automated Verification
                                                         ↓
                                            Test Case Generation
                                                         ↓
                                            Developer Fix Process
                                                         ↓
                                            Automated Retest → Notify User
```

---

## Error Report Data Structure

```json
{
  "error_id": "ERR-20251008-abc123",
  "timestamp": "2025-10-08T14:30:00Z",
  "status": "new",
  "error_type": "contraindicated|wrong_drug|wrong_dose|missed_allergy|wrong_route|other",
  "severity": "low|medium|high|critical",
  "error_description": "Free text from pharmacist",
  "expected_recommendation": "What should have been recommended",
  "reporter_name": "Pharmacist name or ID (optional)",
  "patient_data": {
    "age": 55,
    "infection_type": "uti",
    "fever": true,
    "allergies": "Penicillin (anaphylaxis)"
  },
  "recommendation_given": {
    "drugs": ["Ceftriaxone"],
    "route": "IV",
    "recommendation": "Full text recommendation"
  }
}
```

---

## Status Workflow

1. **new**: Error just reported by pharmacist
2. **verified**: Automated script reproduced the error
3. **in_progress**: Developer actively working on fix
4. **fixed**: Fix implemented and tests passing
5. **closed**: Pharmacist notified, issue resolved
6. **wont_fix**: Determined not to be an error (edge case)
7. **not_reproduced**: Could not reproduce (may already be fixed)

---

## Implementation Phases

### Phase 1: Error Reporting Infrastructure ✅ IN PROGRESS
**Goal**: Enable pharmacists to submit error reports

**Components**:
- Frontend error report modal (Alpine.js)
- Backend API endpoints (FastAPI)
- JSONL storage system
- Admin API to retrieve/update reports

**Files**:
- `logs/error_reports/YYYY-MM-DD.jsonl`
- API endpoints in `fastapi_server.py`
- Frontend modal in `alpine_frontend.html`

---

### Phase 2: Automated Verification
**Goal**: Automatically verify reported errors and generate test cases

**Components**:
- `scripts/verify_error_reports.py` - Verification script
- `tests/test_error_reports.py` - Generated test cases
- Status update mechanism

**Process**:
1. Read error reports with status='new'
2. Reproduce error with current system
3. If reproduced → generate pytest test case
4. Update status to 'verified' or 'not_reproduced'

---

### Phase 3: Fix Workflow
**Goal**: Streamline developer fix process

**Components**:
- `scripts/fix_verified_errors.py` - Interactive fix workflow
- Documentation for developers
- Regression testing automation

**Process**:
1. Display verified errors
2. Run error tests (should fail)
3. Developer makes fix (JSON or code)
4. Re-run error tests (should pass)
5. Run full test suite (check regressions)
6. Update status to 'fixed'

---

### Phase 4: Monitoring & Feedback
**Goal**: Close the loop with pharmacists

**Components**:
- Admin dashboard (view all error reports)
- Metrics: error rate, time-to-fix, severity distribution
- Notification system (email/Slack) for critical errors
- Feedback to pharmacist when error fixed

---

## API Endpoints

### POST /api/error-report
Submit error report from pharmacist
```json
{
  "error_type": "contraindicated",
  "severity": "high",
  "error_description": "Gave ceftriaxone to severe PCN allergy",
  "expected_recommendation": "Should have given aztreonam",
  "reporter_name": "Dr. Smith",
  "patient_data": {...},
  "recommendation_given": {...}
}
```

**Response**:
```json
{
  "success": true,
  "error_id": "ERR-20251008-abc123",
  "message": "Error report submitted successfully"
}
```

---

### GET /api/error-reports
Retrieve error reports (admin)

**Query Parameters**:
- `status`: Filter by status (new, verified, fixed, etc.)
- `severity`: Filter by severity (low, medium, high, critical)

**Response**:
```json
{
  "success": true,
  "count": 5,
  "reports": [...]
}
```

---

### PATCH /api/error-report/{error_id}/status
Update error report status

**Query Parameters**:
- `new_status`: new|verified|in_progress|fixed|closed|wont_fix

**Response**:
```json
{
  "success": true,
  "message": "Error ERR-20251008-abc123 status updated to verified"
}
```

---

## Test Case Generation

Error reports automatically generate pytest test cases:

```python
def test_error_report_ERR_20251008_abc123(engine):
    """
    Error Report: ERR-20251008-abc123
    Type: contraindicated
    Severity: high

    Description: Gave ceftriaxone to severe PCN allergy
    Expected: Aztreonam
    """
    patient_data = {
        'age': 55,
        'infection_type': 'uti',
        'fever': True,
        'allergies': 'Penicillin (anaphylaxis)'
    }

    result = engine.get_recommendation(patient_data)

    # Should give aztreonam
    assert 'Aztreonam' in [d['drug_name'] for d in result['drugs']]

    # Should NOT give ceftriaxone (contraindicated)
    assert 'Ceftriaxone' not in [d['drug_name'] for d in result['drugs']]

    # Should classify allergy correctly
    assert result['allergy_classification'] == 'severe_pcn_allergy'
```

---

## Critical Scenarios

### Scenario 1: Critical Error (Patient Safety)
**Trigger**: severity='critical'
**Action**:
1. Immediate Slack notification to dev team
2. Email to medical director
3. Flag in audit log
4. Priority fix (same day)

### Scenario 2: High Severity Error
**Trigger**: severity='high'
**Action**:
1. Daily digest email
2. Verify within 24 hours
3. Fix within 48 hours

### Scenario 3: Medium/Low Severity
**Trigger**: severity='medium' or 'low'
**Action**:
1. Weekly review
2. Batch fixes in next sprint

---

## Automation Schedule

### Daily (Cron Job)
```bash
# Run at 2 AM daily
0 2 * * * cd /path/to/project && /path/to/venv/bin/python scripts/verify_error_reports.py
```

### On-Demand
```bash
# Verify new error reports
python scripts/verify_error_reports.py

# Fix workflow (interactive)
python scripts/fix_verified_errors.py
```

---

## Metrics to Track

1. **Error Volume**
   - Total errors per week
   - Errors by type (contraindicated, wrong_drug, etc.)
   - Errors by severity

2. **Response Time**
   - Time from report to verification
   - Time from verification to fix
   - Time from fix to deployment

3. **Quality Metrics**
   - % of errors reproduced
   - % of fixes that introduced regressions
   - % of errors marked wont_fix

4. **User Satisfaction**
   - Pharmacist feedback on process
   - # of duplicate reports (suggests unfixed issue)
   - # of follow-up reports on same issue

---

## HIPAA Compliance

### De-identification Required
Remove from error reports:
- Patient name
- MRN (Medical Record Number)
- Date of birth
- Admission date/time
- Any other PHI per 18 HIPAA identifiers

### Retained (Safe Harbor)
- Age (not date of birth)
- Infection type
- Allergies (descriptive, not linked to identity)
- Lab values
- Clinical parameters (CrCl, weight)

### Audit Trail
- All error reports logged
- All status changes logged with timestamp
- All fixes logged in git commits

---

## Success Criteria

**Phase 1 Complete**:
- ✅ Pharmacist can submit error report via UI
- ✅ Error saved to JSONL with unique ID
- ✅ Admin can retrieve error reports via API
- ✅ Status can be updated via API

**Phase 2 Complete**:
- ✅ Verification script can reproduce errors
- ✅ Test cases automatically generated
- ✅ Status updated to 'verified' if reproduced

**Phase 3 Complete**:
- ✅ Fix workflow script guides developer
- ✅ Error tests run before and after fix
- ✅ Full test suite runs to check regressions
- ✅ Status updated to 'fixed' when all tests pass

**Phase 4 Complete**:
- ✅ Admin dashboard shows all error reports
- ✅ Metrics dashboard tracks KPIs
- ✅ Pharmacist notified when error fixed
- ✅ Critical errors trigger immediate alerts

---

## Developer Documentation

### How to Fix a Verified Error

1. **Review Error Report**
```bash
# View verified errors
curl http://localhost:8080/api/error-reports?status=verified | jq
```

2. **Run Error Tests (Should Fail)**
```bash
pytest tests/test_error_reports.py -v
```

3. **Make Fix**
- Update JSON guideline files: `guidelines/drugs/*.json` or `guidelines/infections/*.json`
- OR update code logic: `lib/*.py`

4. **Re-run Error Tests (Should Pass)**
```bash
pytest tests/test_error_reports.py -v
```

5. **Run Full Test Suite (Check Regressions)**
```bash
pytest tests/test_comprehensive_cases.py -v
```

6. **Update Status**
```bash
curl -X PATCH "http://localhost:8080/api/error-report/ERR-20251008-abc123/status?new_status=fixed"
```

7. **Commit Fix**
```bash
git add .
git commit -m "Fix ERR-20251008-abc123: Severe PCN allergy now uses aztreonam"
git push
```

---

## Future Enhancements

1. **Machine Learning**
   - Cluster similar error reports
   - Predict error types from description
   - Auto-suggest fixes based on past fixes

2. **Integration**
   - JIRA/Linear integration for tracking
   - Slack bot for reporting errors
   - EHR integration for real-time feedback

3. **Analytics**
   - Root cause analysis dashboard
   - Error pattern detection
   - Proactive error prevention

4. **Gamification**
   - Leaderboard for pharmacists reporting errors
   - Badges for different error types found
   - Impact metrics (errors prevented downstream)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-08
**Owner**: Development Team
**Review Frequency**: Weekly during pilot phase
