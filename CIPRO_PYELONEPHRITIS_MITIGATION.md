# Ciprofloxacin Pyelonephritis Issue - Mitigation Plan

## Problem Statement
After deployment, the antibiotic steward system is incorrectly recommending **oral ciprofloxacin (Cipro)** as the first-line agent for pyelonephritis, when it should recommend **IV Ceftriaxone**.

## Root Cause Analysis

### Investigation Findings
1. ✅ **Routing is CORRECT**: `pyelonephritis` → `TUHS_Pyelonephritis_Expert` agent
2. ✅ **JSON Guidelines are CORRECT**: ABXguideInp.json lines 184-202 specify:
   - Community-acquired pyelonephritis: **Ceftriaxone IV** (first-line)
   - Hospital-acquired pyelonephritis: **Piperacillin-tazobactam IV OR Cefepime IV**
   - NO ciprofloxacin mentioned in pyelonephritis section
3. ✅ **Agent Instructions are CORRECT**: Generated pyelonephritis instructions show Ceftriaxone IV as first-line (instruction line 19)
4. ❌ **Ciprofloxacin source**: Appears ONLY in **Cystitis** section (ABXguideInp.json:127, 135) as last-resort for contraindications

### Most Likely Root Causes
1. **AI Model Confusion**: The Agno agent may be confusing Cystitis and Pyelonephritis guidelines despite correct routing
2. **Instruction Ambiguity**: Line 42 of generated instructions states "Always select an IV formulation. The only indication for selecting an Oral formulation is in addition to an IV formulation, or for uncomplicated cystitis" - may cause cross-referencing
3. **Pregnancy Guidance Cross-Contamination**: Lines 56-61 mention both Cystitis and Pyelonephritis in same pregnancy guidance section

## Mitigation Strategies (Ranked by Impact)

### Strategy 1: Add Explicit NEGATIVE Instructions (HIGH PRIORITY)
**Impact**: HIGH | **Effort**: LOW | **Risk**: VERY LOW

Add explicit prohibition of ciprofloxacin for pyelonephritis in agent instructions.

**Implementation**:
```python
# In agno_bridge_v2.py, after line 178, add:
instructions.append("")
instructions.append("🚨 PYELONEPHRITIS-SPECIFIC WARNINGS:")
instructions.append("- NEVER use Ciprofloxacin (oral or IV) as first-line for pyelonephritis")
instructions.append("- NEVER use oral antibiotics as first-line for pyelonephritis")
instructions.append("- Community-acquired pyelonephritis: Ceftriaxone IV is MANDATORY first-line")
instructions.append("- Hospital-acquired pyelonephritis: Piperacillin-tazobactam IV OR Cefepime IV")
instructions.append("- Fluoroquinolones are NOT recommended for pyelonephritis in TUHS guidelines")
```

**File**: `agno_bridge_v2.py:178-185` (insert after "IMPORTANT:" section, before pregnancy considerations)

### Strategy 2: Strengthen Instruction Clarity (MEDIUM PRIORITY)
**Impact**: MEDIUM | **Effort**: LOW | **Risk**: VERY LOW

Modify line 176 to be more specific about pyelonephritis vs cystitis distinction.

**Implementation**:
```python
# Replace line 176 in agno_bridge_v2.py:
# OLD:
instructions.append("- Always select an IV formulation. The only indication for selecting an Oral formulation is in addition to an IV formulation, or for uncomplicated cystitis")

# NEW:
if subsection_filter and "pyelonephritis" in subsection_filter.lower():
    instructions.append("- PYELONEPHRITIS REQUIRES IV ANTIBIOTICS. Never use oral-only therapy for pyelonephritis.")
    instructions.append("- You are treating PYELONEPHRITIS (febrile UTI), NOT simple cystitis. Use IV ceftriaxone as first-line.")
else:
    instructions.append("- Always select an IV formulation. The only indication for selecting an Oral formulation is in addition to an IV formulation, or for uncomplicated cystitis")
```

**File**: `agno_bridge_v2.py:176`

### Strategy 3: Separate Pregnancy Guidance (MEDIUM PRIORITY)
**Impact**: MEDIUM | **Effort**: MEDIUM | **Risk**: LOW

Split the combined UTI pregnancy guidance into infection-specific sections to prevent cross-contamination.

**Implementation**:
```python
# In agno_bridge_v2.py, replace lines 193-200 with:
if infection_name == "Urinary Tract":
    if subsection_filter and "pyelonephritis" in subsection_filter.lower():
        instructions.append("")
        instructions.append("🤰 PYELONEPHRITIS-SPECIFIC PREGNANCY GUIDANCE:")
        instructions.append("- Pregnant + Pyelonephritis: Ceftriaxone IV is MANDATORY first-line (safe, effective, IV ONLY)")
        instructions.append("- Pregnant + PCN allergy (severe): Aztreonam IV ± Vancomycin IV (IV ONLY)")
        instructions.append("- NEVER use oral ciprofloxacin for pyelonephritis in pregnancy")
        instructions.append("- AVOID in pregnancy: Fluoroquinolones, TMP/SMX (teratogenic in 1st trimester)")
        instructions.append("- Duration in pregnancy: Usually 7-14 days (longer than non-pregnant)")
    elif subsection_filter and "cystitis" in subsection_filter.lower():
        instructions.append("")
        instructions.append("🤰 CYSTITIS-SPECIFIC PREGNANCY GUIDANCE:")
        instructions.append("- Pregnant + Cystitis: Nitrofurantoin PO (avoid near term), Cephalexin PO, Fosfomycin PO")
        instructions.append("- AVOID in pregnancy: Fluoroquinolones, TMP/SMX (teratogenic in 1st trimester)")
        instructions.append("- Duration in pregnancy: Usually 7 days")
```

**File**: `agno_bridge_v2.py:193-200`

### Strategy 4: Add Validation Layer (LOW PRIORITY - Future Enhancement)
**Impact**: HIGH | **Effort**: HIGH | **Risk**: MEDIUM

Create a post-processing validation step that rejects ciprofloxacin recommendations for pyelonephritis.

**Implementation**:
```python
# In agno_bridge_v2.py, after line 435, add validation:
def _validate_recommendation(self, category: str, response: str) -> tuple[bool, str]:
    """Validate recommendation against known contraindications"""

    if category == InfectionCategory.PYELONEPHRITIS:
        # Check for prohibited drugs
        if 'ciprofloxacin' in response.lower() or 'cipro' in response.lower():
            return False, "ERROR: Ciprofloxacin detected in pyelonephritis recommendation. This violates TUHS guidelines. Regenerating..."

        # Require IV antibiotics
        if not any(iv_drug in response.lower() for iv_drug in ['ceftriaxone', 'cefepime', 'piperacillin', 'aztreonam']):
            return False, "ERROR: No appropriate IV antibiotic detected for pyelonephritis. Regenerating..."

    return True, ""

# Then in process_request(), after line 435:
is_valid, error_msg = self._validate_recommendation(category, tuhs_response)
if not is_valid:
    print(f"⚠️  {error_msg}")
    # Optionally: retry with stronger prompt or return error
```

**File**: `agno_bridge_v2.py` (new method + call in process_request)

### Strategy 5: Model Temperature Adjustment (LOWEST PRIORITY)
**Impact**: LOW | **Effort**: LOW | **Risk**: MEDIUM

Reduce model temperature to make responses more deterministic and guideline-adherent.

**Implementation**:
```python
# In agno_bridge_v2.py, line 229-235, modify base_model creation:
base_model = OpenAIChat(
    id="google/gemini-2.0-flash-exp:free",
    api_key=self.api_key,
    base_url="https://openrouter.ai/api/v1",
    temperature=0.1  # CHANGED from default (likely 0.7) to 0.1 for more deterministic output
)
```

**File**: `agno_bridge_v2.py:229-235`

## Recommended Implementation Order

1. **IMMEDIATE (Deploy Today)**:
   - Strategy 1: Add explicit negative instructions (15 minutes)
   - Strategy 2: Strengthen instruction clarity (10 minutes)

2. **SHORT-TERM (Deploy This Week)**:
   - Strategy 3: Separate pregnancy guidance (30 minutes)
   - Strategy 5: Reduce model temperature (5 minutes)

3. **LONG-TERM (Future Enhancement)**:
   - Strategy 4: Add validation layer (2-3 hours)

## Testing Plan

After implementing Strategies 1 & 2, test with:

```bash
curl -X POST http://localhost:8080/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "age": "35",
    "gender": "female",
    "location": "Ward",
    "infection_type": "pyelonephritis",
    "gfr": "85",
    "allergies": "None",
    "culture_results": "",
    "prior_resistance": "",
    "inf_risks": ""
  }'
```

**Expected Output**: Must contain "Ceftriaxone IV" as first-line recommendation, NO ciprofloxacin

## Monitoring

- Add logging to track when ciprofloxacin appears in any pyelonephritis recommendation
- Alert if validation layer (Strategy 4) triggers more than once per day
- Review audit logs for pyelonephritis recommendations weekly

## Success Criteria

- ✅ 0 instances of ciprofloxacin recommended for pyelonephritis in 100 test cases
- ✅ Ceftriaxone IV appears as first-line in >95% of community-acquired pyelonephritis cases
- ✅ No user complaints about inappropriate oral antibiotics for pyelonephritis

## Files to Modify

1. `agno_bridge_v2.py` (primary file)
2. `CIPRO_PYELONEPHRITIS_MITIGATION.md` (this file - for documentation)
3. Test files (to add regression tests)

## Rollback Plan

If mitigation causes issues:
1. Revert `agno_bridge_v2.py` to previous version
2. Restart FastAPI server
3. Review model behavior with increased verbosity

## Contact

If issues persist after implementing Strategies 1-3, escalate to:
- Infectious Disease team for guideline review
- AI/ML team for model behavior analysis
