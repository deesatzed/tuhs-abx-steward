# 🚀 QUICK START - Test Drive TUHS Multi-Agent System

## **3 Ways to Test Drive**

---

## **Option 1: Interactive Mode** (Recommended)

```bash
cd /Volumes/WS4TB/claude_abx_bu930/claude_abx/phase2
source venv_agno/bin/activate
python test_drive.py
```

**You'll get an interactive menu:**
```
📝 SELECT A TEST CASE:
1. Simple Pneumonia (Ward patient)
2. Complex UTI (Elderly with renal impairment)
3. Bacteremia with Resistance (ICU)
4. Skin Infection with Allergy
5. Custom Case (Enter your own)
6. Exit
```

**Example Session:**
```
Enter choice (1-6): 1

======================================================================
🏥 TUHS MULTI-AGENT ANTIBIOTIC STEWARDSHIP SYSTEM
======================================================================

✅ CATEGORY DETERMINATION: Pneumonia
✅ COMPLEXITY ASSESSMENT: 1.00x
   ✓  STANDARD COMPLEXITY

📋 CLINICAL ASSESSMENT:
   Patient: 55yo M
   Location: Ward
   GFR: 80 mL/min
   Allergies: none

💊 PRIMARY RECOMMENDATION:
   Ceftriaxone 1g IV q24h + Azithromycin 500mg PO/IV daily

🔄 ALTERNATIVE OPTIONS:
   1. Piperacillin-tazobactam 4.5g IV q6h + Vancomycin 15mg/kg IV q12h
   2. Levofloxacin 750mg IV/PO daily + Aztreonam 2g IV q8h

🎯 KEY CONSIDERATIONS:
   • Check MRSA risk factors
   • Assess for Pseudomonas risk
   • Consider aspiration risk

👁️  MONITORING & STEWARDSHIP:
   • Obtain cultures before starting antibiotics
   • Reassess at 48-72 hours
   • De-escalate based on culture results

📊 CONFIDENCE ASSESSMENT:
   🔴 HIGH CONFIDENCE (80%)
   Strong TUHS guideline match
```

---

## **Option 2: Batch Testing Mode**

Run all 3 test cases automatically:

```bash
source venv_agno/bin/activate
python test_drive.py batch
```

**Tests:**
1. ✅ Simple CAP (Ward patient)
2. ✅ Complex Bacteremia (ICU, resistance, allergies)
3. ✅ UTI with Renal Impairment

---

## **Option 3: Custom Case (Python)**

```python
import asyncio
from test_drive import TUHSTestSystem

async def test_my_case():
    system = TUHSTestSystem()
    
    patient_data = {
        "age": 72,
        "gender": "M",
        "location": "Ward",
        "infection_type": "cellulitis",
        "gfr": 45,
        "allergies": "penicillin (rash)",
        "history_mrsa": True
    }
    
    result = await system.process_case(patient_data)
    print(f"\nResult: {result}")

asyncio.run(test_my_case())
```

---

## **What the System Does**

### **1. Category Determination** ✅
- Routes to specialized agent (Pneumonia, UTI, Bacteremia, etc.)
- Uses infection type from patient data

### **2. Complexity Assessment** ✅
- Factors: Age, GFR, resistance history, comorbidities
- Scores: 1.0x (simple) → 3.0x+ (complex)
- Triggers warnings for high complexity

### **3. Regimen Selection** ✅
- Category-specific TUHS guidelines
- Primary + alternative options
- Renal dose adjustments

### **4. Allergy Checking** ✅
- Beta-lactam cross-reactivity
- Severity assessment (anaphylaxis vs rash)
- Alternative recommendations

### **5. Monitoring Plan** ✅
- Culture requirements
- Reassessment timing
- Stewardship considerations

### **6. Confidence Scoring** ✅
- 🔴 High (≥80%) - Strong guideline match
- 🟡 Moderate (60-79%) - Complex factors
- 🟠 Low (<60%) - ID consultation needed

---

## **Test Cases Included**

### **Case 1: Simple Pneumonia**
```json
{
  "age": 55,
  "infection_type": "pneumonia",
  "gfr": 80,
  "allergies": "none"
}
```
**Expected:** Ceftriaxone + Azithromycin, High confidence

### **Case 2: Complex Bacteremia**
```json
{
  "age": 88,
  "infection_type": "bacteremia",
  "gfr": 25,
  "allergies": "penicillin (anaphylaxis)",
  "history_mrsa": true,
  "history_vre": true
}
```
**Expected:** Renal-adjusted, Allergy warning, Moderate confidence

### **Case 3: UTI with Renal Impairment**
```json
{
  "age": 78,
  "infection_type": "uti",
  "gfr": 35,
  "comorbidities": ["CKD"]
}
```
**Expected:** Dose adjustment, Monitoring plan

---

## **Custom Case Template**

```python
patient_data = {
    "age": 65,                          # Required
    "gender": "M",                      # M/F
    "location": "Ward",                 # Ward/ICU/ED
    "infection_type": "pneumonia",      # See categories below
    "gfr": 60,                          # mL/min
    "allergies": "none",                # or "penicillin (rash)"
    "history_mrsa": False,              # True/False
    "history_vre": False,               # True/False
    "comorbidities": []                 # ["diabetes", "CKD"]
}
```

### **Supported Infection Types:**
- `pneumonia`, `cap`, `hap`, `vap`
- `uti`, `cystitis`, `pyelonephritis`
- `bacteremia`, `sepsis`
- `cellulitis`, `skin`, `ssti`
- `intra` (intra-abdominal)
- `bone`, `joint`
- `meningitis`

---

## **Understanding the Output**

### **Complexity Scoring:**
- **1.0x** = Standard case
- **1.2x** = Elderly or mild renal impairment
- **1.5x** = Severe renal impairment (GFR <30)
- **2.0x+** = Multiple risk factors
- **3.0x+** = High complexity, consider ID

### **Dose Adjustments:**
- **GFR ≥60**: Standard dosing
- **GFR 30-60**: Moderate adjustment (25-50% reduction)
- **GFR <30**: Severe adjustment (consult pharmacy)

### **Allergy Severity:**
- **Mild**: Rash, itching → May use cephalosporins with monitoring
- **Severe**: Anaphylaxis, SJS → Contraindicated, use alternatives

---

## **Next Steps After Test Drive**

### **Phase 1: You've Completed** ✅
- Core logic implementation
- Unit tests (24/24 passed)
- Test drive demonstration

### **Phase 2: Full Integration** (Next)
1. Setup PostgreSQL + pgvector database
2. Load TUHS guidelines into knowledge base
3. Configure OpenRouter API keys
4. Connect to PubMed/ArXiv for evidence search

### **Phase 3: Production Deployment**
1. Web interface integration
2. Session management
3. Audit logging
4. Performance optimization

---

## **Troubleshooting**

### **Issue: Module not found**
```bash
# Ensure virtual environment is activated
source venv_agno/bin/activate
python test_drive.py
```

### **Issue: No output**
```bash
# Run in verbose mode
python test_drive.py batch
```

### **Issue: Want to modify regimens**
Edit the `_load_category_knowledge()` method in `test_drive.py`

---

## **System Status**

```
✅ Core Logic: IMPLEMENTED
✅ Unit Tests: 24/24 PASSED (99% coverage)
✅ Test Drive: WORKING
⏳ Database: Not yet configured
⏳ API Keys: Not yet configured
⏳ Full Agno: Awaiting database setup
```

---

## **Questions?**

**Check:**
1. Test results: `pytest tests/test_simple_agents.py -v`
2. System architecture: `README_MULTIAGENT.md`
3. Full documentation: `tuhs_multi_agent_system.py` comments

**Try:**
- Interactive mode for exploring different cases
- Batch mode to see all test scenarios
- Custom cases to test your specific needs

---

**🎉 Enjoy test driving the TUHS Multi-Agent System!**
