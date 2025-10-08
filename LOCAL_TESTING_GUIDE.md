# Local Testing Guide
## TUHS Antibiotic Steward - Running and Testing Locally

---

## Prerequisites

✅ Python 3.12+ installed
✅ All dependencies installed (Flask, Agno, etc.)
✅ OPENROUTER_API_KEY in `.env` file

---

## Option 1: Test with FastAPI Server (Recommended)

### 1. Start the FastAPI Server

```bash
# From project root directory
python fastapi_server.py
```

Expected output:
```
✅ Loaded split TUHS guidelines:
   - ABX_Selection.json
   - ABX_Dosing.json
✅ Pneumonia agent: 104 instruction lines from JSON
✅ Cystitis agent: 74 instruction lines from JSON
✅ Pyelonephritis agent: 88 instruction lines from JSON
...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

### 2. Test with Web Browser

Open browser to: **http://localhost:8080**

You should see the Alpine.js frontend interface.

### 3. Test with curl (API directly)

**Simple pyelonephritis case:**
```bash
curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "45",
    "gender": "female",
    "location": "Ward",
    "infection_type": "pyelonephritis",
    "gfr": "85",
    "allergies": "None"
  }'
```

Expected response:
```json
{
  "category": "pyelonephritis",
  "tuhs_recommendation": "Recommended antibiotics: Ceftriaxone IV for pyelonephritis",
  "tuhs_confidence": 0.9,
  "evidence_search_performed": false,
  "evidence_results": [],
  "final_confidence": 0.9
}
```

**Bacteremia with anaphylaxis (critical safety test):**
```bash
curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "88",
    "gender": "male",
    "location": "Ward",
    "infection_type": "bacteremia",
    "gfr": "44",
    "allergies": "Penicillin (anaphylaxis)",
    "inf_risks": "MRSA colonization"
  }'
```

Expected response should contain:
- ✅ Aztreonam + Vancomycin
- ❌ NO cephalosporins (cefepime, ceftriaxone)

**Pregnant patient with pyelonephritis:**
```bash
curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "28",
    "gender": "female",
    "location": "Ward",
    "infection_type": "pyelonephritis",
    "gfr": "95",
    "allergies": "None",
    "inf_risks": "Pregnancy - 26 weeks gestation"
  }'
```

Expected response should contain:
- ✅ Ceftriaxone IV
- ❌ NO fluoroquinolones (ciprofloxacin, levofloxacin)

### 4. Test Health Endpoint

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-07T12:34:56.789Z",
  "version": "2.0",
  "guidelines_loaded": true
}
```

### 5. View API Documentation

Open browser to: **http://localhost:8080/docs**

This opens Swagger UI with interactive API documentation.

---

## Option 2: Run Automated Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Only Critical Safety Tests
```bash
pytest tests/ -v -m critical
```

### Run Only Allergy Tests
```bash
pytest tests/ -v -m allergy
```

### Run Single E2E Scenario
```bash
pytest tests/test_e2e_scenarios.py::TestCriticalClinicalScenarios::test_scenario_1_pyelonephritis_no_allergy -v -s
```

The `-s` flag shows all print statements, so you can see the actual API responses.

### Run Tests with Detailed Output
```bash
pytest tests/test_drug_selection_allergy.py::TestSeverePenicillinAllergy::test_bacteremia_anaphylaxis_no_cephalosporins -v -s
```

This will show:
- Guidelines loading
- Agent initialization
- API request/response
- Validation results

---

## Option 3: Interactive Python Testing

### 1. Start Python REPL

```bash
python
```

### 2. Test the Backend Bridge Directly

```python
import asyncio
from agno_bridge_v2 import AgnoBackendBridge
import os

# Ensure API key is loaded
api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('OPENROUTER_API_KEY')

# Create bridge
bridge = AgnoBackendBridge(api_key=api_key)

# Test simple case
patient_data = {
    'age': '45',
    'gender': 'female',
    'location': 'Ward',
    'infection_type': 'pyelonephritis',
    'gfr': '85',
    'allergies': 'None'
}

# Run async request
result = asyncio.run(bridge.process_request(patient_data))

# View results
print(f"Category: {result['category']}")
print(f"Recommendation: {result['tuhs_recommendation']}")
print(f"Confidence: {result['tuhs_confidence']}")
```

### 3. Test Critical Safety Case (Anaphylaxis)

```python
# Test bacteremia + anaphylaxis
patient_data_anaphylaxis = {
    'age': '88',
    'gender': 'male',
    'location': 'Ward',
    'infection_type': 'bacteremia',
    'gfr': '44',
    'allergies': 'Penicillin (anaphylaxis)',
    'inf_risks': 'MRSA colonization'
}

result = asyncio.run(bridge.process_request(patient_data_anaphylaxis))
recommendation = result['tuhs_recommendation'].lower()

print(f"Recommendation: {result['tuhs_recommendation']}")

# Verify safety
assert 'aztreonam' in recommendation, "Should have aztreonam"
assert 'vancomycin' in recommendation, "Should have vancomycin"
assert 'cefepime' not in recommendation, "CRITICAL: Should NOT have cefepime!"
assert 'ceftriaxone' not in recommendation, "CRITICAL: Should NOT have ceftriaxone!"

print("✅ Safety checks passed!")
```

---

## Option 4: Test with Postman/Insomnia

### Import Collection

Create a new POST request:
- **URL:** `http://localhost:8080/api/recommendation`
- **Method:** POST
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**

```json
{
  "age": "45",
  "gender": "female",
  "location": "Ward",
  "infection_type": "pyelonephritis",
  "gfr": "85",
  "allergies": "None"
}
```

### Test Cases Collection

Save these as separate requests:

**1. Simple Pyelonephritis**
```json
{
  "age": "45",
  "gender": "female",
  "location": "Ward",
  "infection_type": "pyelonephritis",
  "gfr": "85",
  "allergies": "None"
}
```
Expected: Ceftriaxone IV

**2. Bacteremia + Anaphylaxis (CRITICAL)**
```json
{
  "age": "88",
  "gender": "male",
  "location": "Ward",
  "infection_type": "bacteremia",
  "gfr": "44",
  "allergies": "Penicillin (anaphylaxis)",
  "inf_risks": "MRSA colonization"
}
```
Expected: Aztreonam + Vancomycin (NO cephalosporins)

**3. Pregnant Pyelonephritis (CRITICAL)**
```json
{
  "age": "28",
  "gender": "female",
  "location": "Ward",
  "infection_type": "pyelonephritis",
  "gfr": "95",
  "allergies": "None",
  "inf_risks": "Pregnancy - 26 weeks gestation"
}
```
Expected: Ceftriaxone (NO fluoroquinolones)

**4. Meningitis**
```json
{
  "age": "45",
  "gender": "male",
  "location": "ICU",
  "infection_type": "meningitis",
  "gfr": "90",
  "allergies": "None"
}
```
Expected: Vancomycin + Ceftriaxone

**5. Septic Shock**
```json
{
  "age": "70",
  "gender": "female",
  "location": "ICU",
  "infection_type": "sepsis",
  "gfr": "35",
  "allergies": "None",
  "inf_risks": "Septic shock, unknown source, intubated"
}
```
Expected: Broad-spectrum + Vancomycin + Metronidazole

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8080
lsof -ti :8080

# Kill the process
lsof -ti :8080 | xargs kill -9
```

### API Key Not Found
```bash
# Check if .env has API key
grep OPENROUTER_API_KEY .env

# Should output:
# OPENROUTER_API_KEY=sk-or-v1-...
```

If missing, add to `.env`:
```bash
echo "OPENROUTER_API_KEY=your-key-here" >> .env
```

### Dependencies Missing
```bash
pip install flask flask-cors agno python-dotenv httpx
```

### Guidelines Not Loading
Check that these files exist:
```bash
ls -lh ABX*.json

# Should show:
# ABX_Selection.json (32KB)
# ABX_Dosing.json (17KB)
# ABXguideInp.json (64KB - legacy fallback)
```

### Tests Failing
```bash
# Ensure environment is set up
pip install pytest pytest-asyncio

# Check API key is available
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', 'Found' if os.getenv('OPENROUTER_API_KEY') else 'Missing')"
```

---

## Monitoring Logs

### View Real-Time Logs
When server is running, you'll see:
```
✅ Category: pyelonephritis
🔍 Querying TUHS pyelonephritis expert...
✅ TUHS response received
📊 TUHS Confidence: 90%
```

### Check Audit Logs
```bash
# View today's audit log
cat logs/audit-$(date +%Y-%m-%d).log | head -20

# Pretty print with jq (if installed)
cat logs/audit-$(date +%Y-%m-%d).log | jq '.'
```

---

## Quick Validation Checklist

Run these tests to validate the system is working correctly:

### ✅ Critical Safety Tests

1. **Pyelonephritis should get Ceftriaxone (NOT ciprofloxacin)**
   ```bash
   pytest tests/test_e2e_scenarios.py::TestCriticalClinicalScenarios::test_scenario_1_pyelonephritis_no_allergy -v
   ```

2. **Anaphylaxis should NEVER get cephalosporins**
   ```bash
   pytest tests/test_drug_selection_allergy.py::TestSeverePenicillinAllergy::test_bacteremia_anaphylaxis_no_cephalosporins -v
   ```

3. **Pregnancy should NEVER get fluoroquinolones**
   ```bash
   pytest tests/test_e2e_scenarios.py::TestCriticalClinicalScenarios::test_scenario_5_pregnant_pyelonephritis -v
   ```

All three must pass before deployment.

---

## Performance Testing

### Test Response Time
```bash
time curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "45",
    "gender": "female",
    "location": "Ward",
    "infection_type": "pyelonephritis",
    "gfr": "85",
    "allergies": "None"
  }'
```

Expected: < 3 seconds for simple cases

### Concurrent Requests (Load Test)
```bash
# Install apache bench if needed: brew install httpd

# Test 100 requests, 10 concurrent
ab -n 100 -c 10 -p test_payload.json -T application/json http://localhost:8080/api/recommendation
```

Create `test_payload.json`:
```json
{
  "age": "45",
  "gender": "female",
  "location": "Ward",
  "infection_type": "pyelonephritis",
  "gfr": "85",
  "allergies": "None"
}
```

---

## Next Steps After Local Testing

1. ✅ All unit tests pass
2. ✅ All critical safety tests pass
3. ✅ Manual testing of web interface works
4. ✅ API responses are correct
5. ✅ No contraindicated drugs recommended
6. → Deploy to staging (Fly.io)
7. → Run same tests against staging
8. → Begin pilot testing with experts

---

## Support

If you encounter issues:
1. Check logs: `logs/audit-$(date +%Y-%m-%d).log`
2. Verify API key: `grep OPENROUTER_API_KEY .env`
3. Check dependencies: `pip list | grep -E 'flask|agno|pytest'`
4. Run health check: `curl http://localhost:8080/health`
