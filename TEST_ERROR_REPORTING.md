# Test Guide: Error Reporting System

**Date**: 2025-10-08
**Purpose**: Manual testing guide for Phase 1 error reporting implementation

---

## Prerequisites

1. FastAPI server must be running on port 8080
2. Python virtual environment activated: `source venv_agno/bin/activate` (or your env)
3. `curl` and `jq` installed (jq optional but helpful)

---

## Step 1: Start the Server

```bash
# Kill any existing servers on port 8080
lsof -ti :8080 | xargs kill -9 2>/dev/null

# Start FastAPI server
python fastapi_server.py
```

**Expected Output**:
```
🚀 TUHS Antibiotic Steward - FastAPI Server
==================================================
📡 API Docs:     /api/docs
🌐 Frontend:     /
❤️  Health:      /health
📝 Error Reports: /api/error-reports
==================================================
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

## Step 2: Test Health Check

```bash
curl http://localhost:8080/health | jq
```

**Expected Output**:
```json
{
  "status": "healthy",
  "backend": "FastAPI",
  "version": "2.0.0",
  "timestamp": "2025-10-08T..."
}
```

---

## Step 3: Submit Test Error Report

### Option A: Using Inline JSON

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "contraindicated",
    "severity": "high",
    "error_description": "System gave ceftriaxone to patient with severe PCN allergy (anaphylaxis)",
    "expected_recommendation": "Should have given aztreonam instead",
    "reporter_name": "Test Pharmacist",
    "patient_data": {
      "age": 55,
      "infection_type": "uti",
      "fever": true,
      "allergies": "Penicillin (anaphylaxis)"
    },
    "recommendation_given": {
      "drugs": ["Ceftriaxone"],
      "route": "IV"
    }
  }' | jq
```

### Option B: Using Test File (Already Created)

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d @/tmp/test_error_report.json | jq
```

**Expected Output**:
```json
{
  "success": true,
  "error_id": "ERR-20251008-xxxxxxxx",
  "message": "Error report submitted successfully. Thank you for helping improve the system."
}
```

**Server Console Output**:
```
📝 Error report submitted: ERR-20251008-xxxxxxxx (severity: high)
```

---

## Step 4: Verify File Created

```bash
# List error report files
ls -la logs/error_reports/

# View the error report
cat logs/error_reports/2025-10-08.jsonl | jq
```

**Expected Output**:
```json
{
  "error_type": "contraindicated",
  "severity": "high",
  "error_description": "System gave ceftriaxone to patient with severe PCN allergy (anaphylaxis)",
  "expected_recommendation": "Should have given aztreonam instead",
  "reporter_name": "Test Pharmacist",
  "patient_data": {
    "age": 55,
    "infection_type": "uti",
    "fever": true,
    "allergies": "Penicillin (anaphylaxis)"
  },
  "recommendation_given": {
    "drugs": ["Ceftriaxone"],
    "route": "IV"
  },
  "error_id": "ERR-20251008-xxxxxxxx",
  "status": "new",
  "created_at": "2025-10-08T..."
}
```

---

## Step 5: Retrieve Error Reports

### Get All Error Reports

```bash
curl http://localhost:8080/api/error-reports | jq
```

**Expected Output**:
```json
{
  "success": true,
  "count": 1,
  "reports": [
    {
      "error_id": "ERR-20251008-xxxxxxxx",
      "status": "new",
      "severity": "high",
      ...
    }
  ],
  "stats": {
    "total": 1,
    "by_status": {
      "new": 1
    },
    "by_severity": {
      "high": 1
    },
    "by_type": {
      "contraindicated": 1
    }
  }
}
```

### Filter by Severity

```bash
# Get only critical errors
curl "http://localhost:8080/api/error-reports?severity=critical" | jq

# Get only high severity errors
curl "http://localhost:8080/api/error-reports?severity=high" | jq
```

### Filter by Status

```bash
# Get only new errors
curl "http://localhost:8080/api/error-reports?status=new" | jq

# Get only verified errors
curl "http://localhost:8080/api/error-reports?status=verified" | jq
```

### Limit Results

```bash
# Get only first 10 errors
curl "http://localhost:8080/api/error-reports?limit=10" | jq
```

---

## Step 6: Update Error Status

### Update to "verified"

```bash
# Replace ERR-20251008-xxxxxxxx with actual error_id from Step 3
curl -X PATCH "http://localhost:8080/api/error-report/ERR-20251008-b3b14df4/status?new_status=verified" | jq
```

**Expected Output**:
```json
{
  "success": true,
  "message": "Error ERR-20251008-xxxxxxxx status updated to verified"
}
```

**Server Console Output**:
```
📝 Updated ERR-20251008-xxxxxxxx: new → verified
```

### Verify Status Update

```bash
# Check the file was updated
cat logs/error_reports/2025-10-08.jsonl | jq '.status, .status_updated_at'
```

**Expected Output**:
```json
"verified"
"2025-10-08T..."
```

---

## Step 7: Test Multiple Error Reports

### Submit Critical Error

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "contraindicated",
    "severity": "critical",
    "error_description": "CRITICAL: Gave cephalosporin to patient with documented cephalosporin anaphylaxis",
    "expected_recommendation": "Should use fluoroquinolone or aztreonam",
    "reporter_name": "Dr. Johnson",
    "patient_data": {
      "age": 68,
      "infection_type": "pneumonia",
      "allergies": "Ceftriaxone - anaphylaxis"
    },
    "recommendation_given": {
      "drugs": ["Ceftriaxone"],
      "route": "IV"
    }
  }' | jq
```

**Expected Server Output**:
```
📝 Error report submitted: ERR-20251008-xxxxxxxx (severity: critical)
🚨 CRITICAL ERROR REPORT: ERR-20251008-xxxxxxxx
   Description: CRITICAL: Gave cephalosporin to patient with documented cephalosporin anaphylaxis
```

### Submit Low Severity Error

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "wrong_dose",
    "severity": "low",
    "error_description": "Dose could be optimized based on weight",
    "expected_recommendation": "Consider weight-based dosing for vancomycin",
    "reporter_name": "PharmD Smith",
    "patient_data": {
      "age": 45,
      "weight": 120,
      "infection_type": "bacteremia"
    },
    "recommendation_given": {
      "drugs": ["Vancomycin 1g q12h"]
    }
  }' | jq
```

---

## Step 8: Test API Documentation

Visit the interactive API documentation:

```bash
# Open in browser
open http://localhost:8080/api/docs
```

**What to Check**:
1. See all error reporting endpoints listed
2. Try "Try it out" feature for each endpoint
3. View request/response schemas
4. Test validation (try invalid severity values)

---

## Step 9: Test Error Cases

### Test Invalid Severity

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "contraindicated",
    "severity": "INVALID",
    "error_description": "Test",
    "expected_recommendation": "Test",
    "patient_data": {},
    "recommendation_given": {}
  }'
```

**Expected Output**:
```json
{
  "detail": "Invalid severity. Must be one of: ['low', 'medium', 'high', 'critical']"
}
```

### Test Invalid Error Type

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "INVALID_TYPE",
    "severity": "high",
    "error_description": "Test",
    "expected_recommendation": "Test",
    "patient_data": {},
    "recommendation_given": {}
  }'
```

**Expected Output**:
```json
{
  "detail": "Invalid error_type. Must be one of: ['contraindicated', 'wrong_drug', ...]"
}
```

### Test Missing Required Field

```bash
curl -X POST http://localhost:8080/api/error-report \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "contraindicated",
    "severity": "high"
  }'
```

**Expected Output**:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "error_description"],
      "msg": "Field required"
    },
    ...
  ]
}
```

---

## Step 10: View Statistics

```bash
# Get summary statistics
curl http://localhost:8080/api/error-reports | jq '.stats'
```

**Expected Output**:
```json
{
  "total": 3,
  "by_status": {
    "new": 2,
    "verified": 1
  },
  "by_severity": {
    "critical": 1,
    "high": 1,
    "low": 1
  },
  "by_type": {
    "contraindicated": 2,
    "wrong_dose": 1
  }
}
```

---

## Verification Checklist

After running all tests, verify:

- [ ] Server starts without errors
- [ ] Health check returns 200 OK
- [ ] Can submit error report successfully
- [ ] Error report file created in `logs/error_reports/YYYY-MM-DD.jsonl`
- [ ] Can retrieve all error reports
- [ ] Can filter by severity
- [ ] Can filter by status
- [ ] Can update error status
- [ ] Status update reflected in file
- [ ] Critical errors logged prominently in console
- [ ] Invalid severity rejected with 400
- [ ] Invalid error_type rejected with 400
- [ ] Missing required fields rejected with 422
- [ ] Statistics calculated correctly
- [ ] API documentation accessible at /api/docs

---

## Cleanup (Optional)

```bash
# Remove test error reports
rm logs/error_reports/2025-10-08.jsonl

# Stop the server
# Press Ctrl+C in the terminal running the server
```

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port 8080 is in use
lsof -i :8080

# Kill any processes using port 8080
lsof -ti :8080 | xargs kill -9
```

### API Returns 404

- Make sure you're using `http://localhost:8080`, not port 3000
- Verify server is running: `curl http://localhost:8080/health`

### File Not Created

- Check directory permissions: `ls -la logs/`
- Verify ERROR_REPORTS_DIR path in fastapi_server.py

---

## Success Criteria

✅ All tests in verification checklist pass
✅ Error reports saved to JSONL files
✅ API endpoints return correct responses
✅ Validation works correctly
✅ Status updates persist to file
✅ Statistics calculated accurately

---

**Test Status**: Ready for manual testing
**Estimated Time**: 15-20 minutes
**Next Step**: Run through all tests and verify checklist
