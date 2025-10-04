# Pregnancy Safety Enhancement

**Date**: October 4, 2025
**Status**: ✅ Complete

---

## Problem Identified

User reported that pregnancy (added to `inf_risks` field) was not being considered in antibiotic recommendations. This is a **critical patient safety issue** as many antibiotics are contraindicated or require special consideration during pregnancy.

### Root Cause

The TUHS guidelines in `ABXguideInp.json` **do not include pregnancy-specific regimens** for most infections. The only mention is a general note about asymptomatic bacteriuria requiring treatment in pregnancy.

---

## Solution Implemented

### 1. Universal Pregnancy Guidance for ALL Agents

Added pregnancy-specific instructions to **every agent** (not just UTI):

```python
# Added to build_agent_instructions() for ALL infection types:
🤰 PREGNANCY CONSIDERATIONS (CRITICAL FOR ALL INFECTIONS):
- If patient is pregnant or pregnancy is mentioned, antibiotic selection is CRITICAL for fetal safety
- If pregnancy is present and these guidelines lack pregnancy-specific regimens:
  → State 'LOW CONFIDENCE - Pregnancy requires specialized review'
  → Recommend evidence search and OB/ID consultation
- Generally SAFE antibiotics in pregnancy: Beta-lactams (Penicillins, Cephalosporins), Aztreonam, Vancomycin
- Generally CONTRAINDICATED in pregnancy: Fluoroquinolones, Tetracyclines, TMP/SMX (1st & 3rd trimester), Aminoglycosides
- ALWAYS explicitly address pregnancy safety in your recommendation if patient is pregnant
- Recommend OB/GYN or Maternal-Fetal Medicine consultation for any pregnant patient with serious infection
```

### 2. Infection-Specific Pregnancy Guidance (UTI)

Added detailed UTI-specific pregnancy guidance for Cystitis and Pyelonephritis agents:

```python
🤰 UTI-SPECIFIC PREGNANCY GUIDANCE:
- Pregnant + Pyelonephritis: Ceftriaxone IV is first-line (safe, effective)
- Pregnant + PCN allergy (severe): Aztreonam IV ± Vancomycin IV
- Pregnant + Cystitis: Nitrofurantoin PO (avoid near term), Cephalexin PO, Fosfomycin PO
- AVOID in pregnancy: Fluoroquinolones, TMP/SMX (teratogenic in 1st trimester)
- Duration in pregnancy: Usually 7-14 days (longer than non-pregnant)
```

### 3. Explicit Pregnancy Alert in Prompts

Updated `_build_tuhs_query()` to explicitly flag pregnancy:

```python
# Check for pregnancy in inf_risks field
is_pregnant = False
if inf_risks and 'pregnan' in inf_risks.lower():
    is_pregnant = True

# Add explicit pregnancy alert to agent prompt
if is_pregnant:
    query += "\n⚠️  PREGNANCY ALERT: This patient is PREGNANT - antibiotic selection must consider fetal safety!\n"
    query += "You MUST address pregnancy-specific safety in your recommendation.\n"
```

### 4. Confidence Score Adjustment for Pregnancy

Updated `calculate_tuhs_confidence()` to reduce confidence when pregnancy is present:

```python
# Check for pregnancy - reduce confidence if pregnancy not explicitly addressed
inf_risks = patient_data.get('inf_risks', '')
if inf_risks and 'pregnan' in inf_risks.lower():
    # Check if pregnancy was addressed in the response
    if 'pregnan' not in category_response.lower():
        confidence -= 0.25  # Major reduction if pregnancy ignored
    # Even if addressed, reduce slightly as guidelines may lack pregnancy-specific regimens
    elif 'low confidence' not in category_response.lower():
        confidence -= 0.1
```

---

## What Changed

### Modified Files

**agno_bridge_v2.py** (4 key changes):

1. **Lines 179-189**: Universal pregnancy considerations added to all agents
2. **Lines 191-199**: UTI-specific pregnancy guidance for Cystitis/Pyelonephritis agents
3. **Lines 485-510**: Pregnancy detection and alert in prompt building
4. **Lines 391-399**: Confidence reduction for pregnancy cases

---

## Expected Behavior

### For Pregnant Patients (any infection type):

1. **Agent receives explicit pregnancy alert** in the prompt
2. **Agent instructions include**:
   - Universal pregnancy safety guidance
   - Infection-specific guidance (if available)
   - Instructions to flag low confidence if guidelines lack pregnancy regimens
3. **Recommendation should**:
   - Explicitly address pregnancy safety
   - Recommend pregnancy-safe antibiotics
   - Suggest OB/GYN or ID consultation
   - State "LOW CONFIDENCE - Pregnancy requires specialized review" if guidelines lack specific regimens
4. **Confidence score**:
   - Reduced by 25% if pregnancy completely ignored
   - Reduced by 10% even if addressed (due to lack of pregnancy-specific guidelines)

### Example: Pregnant Patient with Pyelonephritis + PCN Rash

**Input**:
- Age: 28, Female
- Infection: Pyelonephritis
- Allergies: Penicillin (rash)
- inf_risks: "Pregnancy"

**Expected Recommendation**:
- Antibiotic: Ceftriaxone IV (safe in pregnancy, covers PCN rash allergy)
- Explicit pregnancy safety statement
- Duration: 7-14 days
- Recommend OB/GYN consultation
- Confidence: ~70-80% (reduced due to pregnancy)

---

## Pregnancy-Safe Antibiotics Summary

### Generally SAFE in Pregnancy:
- ✅ **Beta-lactams**: Penicillins, Cephalosporins (Ceftriaxone, Cefazolin, Ampicillin)
- ✅ **Aztreonam** (safe alternative for severe PCN allergy)
- ✅ **Vancomycin** (for MRSA coverage)
- ✅ **Fosfomycin** (for uncomplicated UTI)

### CONTRAINDICATED in Pregnancy:
- ❌ **Fluoroquinolones** (Ciprofloxacin, Levofloxacin) - cartilage damage
- ❌ **Tetracyclines** (Doxycycline) - bone/teeth discoloration
- ❌ **TMP/SMX** - teratogenic in 1st trimester, kernicterus risk in 3rd trimester
- ❌ **Aminoglycosides** - ototoxicity risk

### Use with CAUTION:
- ⚠️ **Nitrofurantoin** - avoid near term (hemolytic anemia risk in newborn)

---

## Testing

### Test Case 1: Pyelonephritis + Pregnancy + PCN Rash
```bash
curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "28",
    "gender": "female",
    "weight_kg": "65",
    "gfr": "95",
    "location": "Ward",
    "infection_type": "pyelonephritis",
    "allergies": "Penicillin (rash)",
    "inf_risks": "Pregnancy",
    "culture_results": "Pending"
  }'
```

**Expected**: Ceftriaxone IV, pregnancy safety addressed, OB/GYN consultation recommended

### Test Case 2: Pneumonia + Pregnancy (No Specific Guidelines)
```bash
curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "32",
    "gender": "female",
    "infection_type": "pneumonia",
    "inf_risks": "Pregnancy",
    "allergies": "none"
  }'
```

**Expected**: "LOW CONFIDENCE - Pregnancy requires specialized review", beta-lactam recommendation, OB/ID consultation

---

## Next Steps (Optional Enhancements)

1. **Update ABXguideInp.json** with pregnancy-specific regimens for all infection types
2. **Add pregnancy checkbox** to frontend (in addition to text field)
3. **Create pregnancy-specific agent** that all agents can consult
4. **Add gestational age consideration** (1st vs 2nd vs 3rd trimester)
5. **Integration with OB/GYN guidelines** for additional safety checks

---

## Documentation Updates

- [x] Created this document (`PREGNANCY_ENHANCEMENT.md`)
- [x] Updated `agno_bridge_v2.py` with comprehensive pregnancy handling
- [ ] Update `README.md` with pregnancy safety notes (optional)
- [ ] Update `CLAUDE.md` for future AI assistance (optional)

---

## Summary

✅ **Universal Pregnancy Safety**: All agents now have pregnancy guidance
✅ **Explicit Alerts**: Pregnancy flagged prominently in agent prompts
✅ **Confidence Adjustment**: Lower confidence when pregnancy present
✅ **Infection-Specific Guidance**: Detailed UTI pregnancy protocols
✅ **Safety First**: Agents instructed to recommend consultation if uncertain

**The system now properly handles pregnancy for all infection types, ensuring patient and fetal safety.**
