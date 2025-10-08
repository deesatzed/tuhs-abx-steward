# Comprehensive Test Suite - 100 Test Cases

**Created**: 2025-10-08
**Purpose**: Validate all input combinations and edge cases for production deployment
**Architecture**: v3 Modular (GuidelineLoader + DrugSelector + DoseCalculator)

---

## Test Coverage Overview

### Total Test Cases: 100

**Breakdown by Category**:
1. **UTI / Pyelonephritis**: 20 cases (Cases 1-20)
2. **Intra-abdominal Infections**: 20 cases (Cases 21-40)
3. **Bacteremia / Sepsis**: 20 cases (Cases 41-60)
4. **Pneumonia**: 15 cases (Cases 61-75)
5. **Meningitis**: 10 cases (Cases 76-85)
6. **Edge Cases & Combinations**: 15 cases (Cases 86-100)

---

## Input Fields Tested

### Patient Demographics
- **Age**: 18-95 years (young adult, middle age, elderly, very elderly)
- **Gender**: Male, female
- **Weight**: 45-150 kg (cachexia to morbid obesity)

### Renal Function
- **GFR/CrCl**: 5-100 mL/min
  - Normal (≥60)
  - Mild impairment (30-59)
  - Moderate impairment (15-29)
  - Severe impairment (<15)
  - ESRD on dialysis

### Location
- **Ward**: Standard hospital admission
- **ICU**: Intensive care unit
- **Emergency**: Emergency department
- **Community**: Community-acquired
- **Hospital**: Hospital-acquired
- **Nursing home**: Long-term care facility

### Infection Types
- **UTI/Pyelonephritis**: Febrile UTI, flank pain
- **Intra-abdominal**: Peritonitis, abscess, post-surgical, perforation, appendicitis, diverticulitis, cholecystitis, SBP
- **Bacteremia**: With/without MRSA risk, central line, endocarditis
- **Pneumonia**: CAP, HAP, VAP, aspiration, severe CAP
- **Meningitis**: Community-acquired, post-neurosurgical, shunt infection

### Allergies
- **None**: No allergies
- **Mild PCN Allergy**: 
  - Rash, mild rash, itching, mild hives
  - Cross-reactivity: <1%
  - Can use: Cephalosporins
- **Severe PCN Allergy**:
  - Anaphylaxis, SJS, DRESS, angioedema
  - Cross-reactivity: Up to 10%
  - Cannot use: ANY beta-lactams
  - Alternative: Aztreonam
- **Multiple Allergies**: PCN + Sulfa combinations

### Prior Resistance Patterns
- **ESBL E. coli**: Extended spectrum beta-lactamase
- **MDR Pseudomonas**: Multi-drug resistant
- **MRSA**: Methicillin-resistant staph aureus
- **C. difficile**: Prior infection history
- **Recent antibiotic use**: Treatment within past months

### Source/Risk Factors
- **Post-surgical**: Recent surgery
- **Central line**: Line-associated infection
- **Mechanical ventilation**: VAP risk
- **Dialysis catheter**: Dialysis-associated
- **Nursing home**: Healthcare-associated
- **Recent hospitalization**: Hospital exposure
- **VP shunt**: Neurosurgical hardware
- **Basilar skull fracture**: Trauma-associated

### Infection Risks (Comorbidities)
- **MRSA colonization**: Known MRSA carrier
- **Neutropenia**: ANC <500
- **Immunosuppressed**: Transplant, HIV, chemotherapy
- **Pregnancy**: 1st, 2nd, 3rd trimester
- **Cirrhosis**: Liver disease
- **ESRD**: End-stage renal disease
- **Diabetes**: Diabetes mellitus
- **COPD**: Chronic lung disease
- **Cystic fibrosis**: CF-related infections
- **Splenectomy/Asplenia**: Increased infection risk
- **Dementia**: Aspiration risk
- **CHF**: Congestive heart failure

---

## Critical Test Cases (Validated)

### Case 1: Standard Pyelonephritis ✅
**Input**: 25yo, pyelonephritis, no allergies, normal renal
**Result**: Ceftriaxone 1g IV q24h
**Status**: PASS

### Case 11: Severe PCN Allergy ✅
**Input**: 55yo, pyelonephritis, PCN anaphylaxis
**Result**: Aztreonam (NO cephalosporins)
**Status**: PASS - Correctly avoids beta-lactams

### Case 31: Intra-abdominal + Severe PCN Allergy ✅
**Input**: 55yo, intra-abdominal, PCN anaphylaxis
**Result**: Aztreonam + Metronidazole + Vancomycin
**Status**: PASS - Triple coverage without beta-lactams

### Case 48: Bacteremia MRSA + Severe PCN Allergy ✅
**Input**: 88yo, bacteremia MRSA, PCN anaphylaxis, renal impairment
**Result**: Aztreonam + Vancomycin
**Status**: PASS - MRSA coverage + gram-negative, no beta-lactams

### Case 76: Meningitis with Loading Dose ✅
**Input**: 25yo, meningitis
**Result**: Ceftriaxone 2g q12h + Vancomycin with loading dose
**Status**: PASS - Higher dose for CNS penetration

### Case 88: Pregnancy + Severe PCN Allergy ✅
**Input**: 28yo, pregnant, pyelonephritis, PCN anaphylaxis
**Result**: Aztreonam
**Status**: PASS - Safe for both pregnancy AND severe allergy

### Case 100: Recent ICU + MRSA Risk ✅
**Input**: 68yo, bacteremia, recent ICU, MRSA risk
**Result**: Vancomycin included
**Status**: PASS - MRSA coverage for high-risk patient

---

## Test Execution

### Run All Tests
```bash
pytest tests/test_comprehensive_cases.py -v
```

### Run Specific Category
```bash
# UTI cases (1-20)
pytest tests/test_comprehensive_cases.py -k "Case1 or Case2 or Case3"

# Severe PCN allergy cases
pytest tests/test_comprehensive_cases.py -k "anaphylaxis"

# Pregnancy cases
pytest tests/test_comprehensive_cases.py -k "pregnancy"

# Renal impairment cases
pytest tests/test_comprehensive_cases.py -k "renal"
```

### Run Critical Safety Cases
```bash
pytest tests/test_comprehensive_cases.py -k "Case11 or Case31 or Case48 or Case88"
```

---

## Validation Checks

Each test case validates:

1. **Success**: Recommendation generated without errors
2. **Expected Drugs**: Correct drug(s) selected
3. **Forbidden Drugs**: Contraindicated drugs NOT selected (critical for allergies)
4. **Route**: IV vs PO appropriateness
5. **Allergy Classification**: Mild vs severe correctly distinguished
6. **Warnings**: Appropriate warnings for renal impairment, elderly, etc.

---

## Edge Cases Covered

### Extreme Ages
- **Case 87**: 18yo (youngest adult)
- **Case 86**: 95yo (very elderly) + multiple comorbidities

### Extreme Weights
- **Case 96**: 45kg (cachexia)
- **Case 95**: 150kg (morbid obesity, BMI 45)

### Severe Renal Impairment
- **Case 4**: CrCl 15 (severe impairment)
- **Case 55**: CrCl 10 (near ESRD)
- **Case 60**: CrCl 5 (ESRD on dialysis)

### Complex Combinations
- **Case 86**: 95yo + CrCl 25 + dementia + CHF
- **Case 88**: Pregnancy + PCN anaphylaxis + pyelonephritis
- **Case 89**: ESRD on dialysis + intra-abdominal + weight 70kg
- **Case 94**: Post-transplant + multiple allergies (PCN + sulfa)

### High-Risk Infections
- **Case 91**: Neutropenic fever (ANC <500)
- **Case 56**: Bone marrow transplant
- **Case 92**: Splenectomy (asplenia)
- **Case 81**: Post-neurosurgical meningitis

---

## Expected Results Summary

### Pyelonephritis (20 cases)
- **No allergy → Ceftriaxone 1g IV q24h** (Cases 1-5)
- **Mild PCN allergy → Ceftriaxone 1g IV q24h** (Cases 6-10)
- **Severe PCN allergy → Aztreonam** (Cases 11-15)
- **Pregnancy → Ceftriaxone** (Cases 16-20)

### Intra-abdominal (20 cases)
- **No allergy → Piperacillin-tazobactam + Metronidazole** (Cases 21-25)
- **Mild PCN allergy → Piperacillin-tazobactam + Metronidazole** (Cases 26-30)
- **Severe PCN allergy → Aztreonam + Metronidazole + Vancomycin** (Cases 31-35)

### Bacteremia (20 cases)
- **No MRSA risk → Ceftriaxone** (Case 41)
- **MRSA risk → Vancomycin + Ceftriaxone** (Cases 42-45)
- **MRSA + Severe PCN allergy → Aztreonam + Vancomycin** (Case 48)

### Meningitis (10 cases)
- **Standard → Ceftriaxone 2g q12h + Vancomycin with loading dose** (Cases 76-85)

---

## Known Limitations (Future Enhancements)

These cases are included but system gives standard empiric therapy:

1. **Case 97**: Prior ESBL E. coli
   - Current: Ceftriaxone (empiric)
   - Future: Should escalate to meropenem

2. **Case 98**: Prior MDR Pseudomonas
   - Current: Standard pneumonia coverage
   - Future: Should use anti-pseudomonal agent

3. **Case 99**: Prior C. diff infection
   - Current: Standard regimen
   - Future: Should minimize unnecessary antibiotics

These require enhancement modules:
- **AntibioticHistoryAnalyzer**
- **CultureGuidedSelector**
- **PriorResistanceEscalator**

---

## Success Criteria

✅ **Pass Rate**: Target 95%+ (allow 5% for data gaps like ESBL/Pseudomonas)
✅ **Safety**: 100% - No contraindicated drugs recommended
✅ **Route**: 100% - All IV-required infections get IV therapy
✅ **Allergy**: 100% - Severe allergies never get cross-reactive drugs

---

## Test Maintenance

### Adding New Cases
```python
TEST_CASES.append({
    'id': 101,
    'name': 'Description of case',
    'input': {patient_data_dict},
    'expected_drugs': ['Drug1'],
    'expected_route': 'IV',
    'expected_allergy': 'mild_pcn_allergy',
    'forbidden_drugs': ['Drug2'],
    'expect_warnings': True
})
```

### Running After Code Changes
```bash
# Full suite
pytest tests/test_comprehensive_cases.py -v

# Quick smoke test (critical cases only)
pytest tests/test_comprehensive_cases.py -k "Case1 or Case11 or Case31 or Case48" -v
```

---

**Test Suite Status**: ✅ READY FOR PRODUCTION
**Coverage**: 100 test cases across all input combinations
**Validation**: Critical safety cases verified
