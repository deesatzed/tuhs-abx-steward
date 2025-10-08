# Build Change Checklist
## JSON Architecture Migration - Two-Part System (Infection → Drug Selection → Dosing)

**Date Started:** 2025-10-08
**Build Version:** 3.0.0
**Status:** 🚧 IN PROGRESS

---

## 📋 Pre-Migration Checks

- [x] Export current conversation for audit trail
- [x] Backup existing JSON files
  - [x] ABX_Selection.json → ABX_Selection.json.backup
  - [x] ABX_Dosing.json → ABX_Dosing.json.backup
  - [x] ABXguideInp.json → ABXguideInp.json.backup
- [ ] Run current test suite and document baseline
  ```bash
  pytest tests/ -v > pre_migration_test_results.txt
  ```
- [ ] Verify server is working with current architecture
  ```bash
  ./quick_test.sh > pre_migration_quick_test.txt
  ```

---

## 🏗️ Phase 1: Directory Structure & Schema Definition

### 1.1 Create Directory Structure
- [ ] Create `guidelines/` root directory
- [ ] Create `guidelines/infections/` directory
- [ ] Create `guidelines/drugs/` directory
- [ ] Create `guidelines/modifiers/` directory
- [ ] Create `guidelines/schemas/` directory for JSON schemas

### 1.2 Create JSON Schemas
- [ ] Create `schemas/infection_schema.json`
- [ ] Create `schemas/drug_schema.json`
- [ ] Create `schemas/allergy_rules_schema.json`
- [ ] Create `schemas/renal_rules_schema.json`
- [ ] Create `schemas/pregnancy_rules_schema.json`

### 1.3 Create Index Registry
- [ ] Create `guidelines/index.json` with file registry

---

## 🔄 Phase 2: Data Migration

### 2.1 Create Infection Files
**CRITICAL: Pyelonephritis MUST require IV antibiotics**

- [ ] Create `guidelines/infections/uti.json`
  - [ ] Include cystitis (oral allowed)
  - [ ] Include pyelonephritis (IV REQUIRED)
  - [ ] Add explicit check: "febrile UTI" = pyelonephritis = IV only
  - [ ] Add warning: NEVER oral antibiotics for pyelonephritis
  - [ ] Test case: Fever + UTI → Must get IV therapy

- [ ] Create `guidelines/infections/pneumonia.json`
  - [ ] CAP (ward)
  - [ ] HAP/VAP
  - [ ] Aspiration pneumonia

- [ ] Create `guidelines/infections/intra_abdominal.json`
  - [ ] Peritonitis
  - [ ] Abscess
  - [ ] Post-surgical

- [ ] Create `guidelines/infections/bacteremia.json`
  - [ ] Sepsis
  - [ ] MRSA coverage scenarios
  - [ ] Central line infections

- [ ] Create `guidelines/infections/meningitis.json`
  - [ ] Bacterial meningitis
  - [ ] Post-neurosurgery

- [ ] Create `guidelines/infections/skin_soft_tissue.json`
  - [ ] Cellulitis
  - [ ] Abscess
  - [ ] Diabetic foot

### 2.2 Create Drug Files
- [ ] Create `guidelines/drugs/ceftriaxone.json`
  - [ ] Include meningitis higher dosing
  - [ ] Include pregnancy safety

- [ ] Create `guidelines/drugs/cefepime.json`
  - [ ] Include renal adjustment requirements

- [ ] Create `guidelines/drugs/piperacillin_tazobactam.json`
  - [ ] Include extended infusion option

- [ ] Create `guidelines/drugs/aztreonam.json`
  - [ ] Safe for severe PCN allergy

- [ ] Create `guidelines/drugs/vancomycin.json`
  - [ ] Loading dose for meningitis
  - [ ] Renal adjustment required

- [ ] Create `guidelines/drugs/metronidazole.json`
  - [ ] Anaerobic coverage

- [ ] Create `guidelines/drugs/azithromycin.json`
  - [ ] Atypical coverage

- [ ] Create `guidelines/drugs/levofloxacin.json`
  - [ ] Respiratory coverage
  - [ ] Pregnancy contraindication

- [ ] Create `guidelines/drugs/ciprofloxacin.json`
  - [ ] Mark as NOT first-line for pyelonephritis
  - [ ] Pregnancy contraindication

- [ ] Create `guidelines/drugs/meropenem.json`
  - [ ] Reserved for resistant organisms

### 2.3 Create Modifier Files
- [ ] Create `guidelines/modifiers/allergy_rules.json`
  - [ ] Mild vs severe classification
  - [ ] Drug class mappings
  - [ ] Cross-reactivity rules
  - [ ] **Explicit**: Rash only = mild = CAN use cephalosporins
  - [ ] **Explicit**: Anaphylaxis/SJS/DRESS = severe = NO beta-lactams

- [ ] Create `guidelines/modifiers/pregnancy_rules.json`
  - [ ] Safe drugs list
  - [ ] Contraindicated drugs (fluoroquinolones, tetracyclines)
  - [ ] Trimester-specific guidance

- [ ] Create `guidelines/modifiers/renal_adjustment_rules.json`
  - [ ] CrCl categories
  - [ ] Per-drug adjustments
  - [ ] Dialysis dosing

---

## 💻 Phase 3: Code Implementation

### 3.1 Create GuidelineLoader Class
- [ ] Create `guideline_loader_v3.py`
- [ ] Implement `_load_infections()` method
- [ ] Implement `_load_drugs()` method
- [ ] Implement `_load_modifiers()` method
- [ ] Implement JSON schema validation
- [ ] Implement cross-reference validation
- [ ] Implement file caching
- [ ] Add hot-reload capability

### 3.2 Create DrugSelector Class
- [ ] Create `drug_selector.py`
- [ ] Implement `select_drugs(patient_data)` method
- [ ] Implement allergy filtering
- [ ] Implement pregnancy filtering
- [ ] Implement route enforcement (IV for pyelonephritis)
- [ ] Add confidence scoring

### 3.3 Create DoseCalculator Class
- [ ] Create `dose_calculator.py`
- [ ] Implement `calculate_doses(drug_ids, patient_data)` method
- [ ] Implement indication-based dosing
- [ ] Implement renal adjustment
- [ ] Implement weight-based calculation
- [ ] Implement loading dose logic

### 3.4 Update AgnoBackendBridge
- [ ] Update to use GuidelineLoader v3
- [ ] Update to use DrugSelector
- [ ] Update to use DoseCalculator
- [ ] Preserve backward compatibility (fallback to old JSON)
- [ ] Update instruction generation

---

## 🧪 Phase 4: Testing & Validation

### 4.1 JSON Schema Tests
- [ ] Test all infection files validate against schema
- [ ] Test all drug files validate against schema
- [ ] Test all modifier files validate against schema

### 4.2 Cross-Reference Tests
- [ ] Test all drug references in infections exist
- [ ] Test all drug IDs are unique
- [ ] Test no orphaned drug files

### 4.3 Critical Safety Tests
**MUST PASS before deployment**

- [ ] **Test: Pyelonephritis gets IV antibiotics (NOT oral)**
  ```python
  patient = {"infection_type": "pyelonephritis", "allergies": "None"}
  result = selector.select_drugs(patient)
  assert all(drug.route == "IV" for drug in result)
  assert "ciprofloxacin" not in [d.name for d in result]  # Cipro is oral
  ```

- [ ] **Test: Febrile UTI recognized as pyelonephritis**
  ```python
  patient = {"infection_type": "uti", "symptoms": "fever", "allergies": "None"}
  result = selector.select_drugs(patient)
  assert result.infection_category == "pyelonephritis"
  assert all(drug.route == "IV" for drug in result)
  ```

- [ ] **Test: Cystitis (no fever) can get oral antibiotics**
  ```python
  patient = {"infection_type": "cystitis", "allergies": "None"}
  result = selector.select_drugs(patient)
  # Oral is allowed for uncomplicated cystitis
  assert any(drug.route == "PO" for drug in result)
  ```

- [ ] **Test: Anaphylaxis → NO cephalosporins**
  ```python
  patient = {"infection_type": "bacteremia", "allergies": "Penicillin (anaphylaxis)"}
  result = selector.select_drugs(patient)
  forbidden = ["ceftriaxone", "cefepime", "cefazolin"]
  assert not any(drug in forbidden for drug in result)
  ```

- [ ] **Test: Mild PCN rash → CAN use cephalosporins**
  ```python
  patient = {"infection_type": "intra_abdominal", "allergies": "Penicillin (rash)"}
  result = selector.select_drugs(patient)
  assert "piperacillin_tazobactam" in result or "cefepime" in result
  ```

- [ ] **Test: Pregnancy → NO fluoroquinolones**
  ```python
  patient = {"infection_type": "pyelonephritis", "allergies": "None", "inf_risks": "Pregnancy"}
  result = selector.select_drugs(patient)
  forbidden = ["ciprofloxacin", "levofloxacin", "moxifloxacin"]
  assert not any(drug in forbidden for drug in result)
  ```

- [ ] **Test: Meningitis → Higher dose ceftriaxone**
  ```python
  patient = {"infection_type": "meningitis", "gfr": "90"}
  drugs = ["ceftriaxone"]
  doses = calculator.calculate_doses(drugs, patient)
  assert "2 g" in doses["ceftriaxone"]
  assert "q12h" in doses["ceftriaxone"]
  ```

### 4.4 Run Full Test Suite
- [ ] Run `pytest tests/ -v`
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] All critical safety tests pass

### 4.5 Manual Testing
- [ ] Run `./quick_test.sh`
- [ ] Test via web interface
- [ ] Test via curl/Postman
- [ ] Test edge cases (dialysis, multiple allergies)

---

## 📦 Phase 5: Deployment Preparation

### 5.1 Update Documentation
- [ ] Update README.md with new architecture
- [ ] Update CLAUDE.md with new file structure
- [ ] Update LOCAL_TESTING_GUIDE.md
- [ ] Create ARCHITECTURE_V3.md documenting new design

### 5.2 Update Dockerfile
- [ ] Copy guidelines/ directory to container
- [ ] Ensure all JSON files are included
- [ ] Remove old ABX_*.json references (keep as backup)

### 5.3 Git Commit
- [ ] Stage all new files
- [ ] Create comprehensive commit message
- [ ] Tag as v3.0.0

### 5.4 Deployment
- [ ] Deploy to staging (Fly.io)
- [ ] Run smoke tests on staging
- [ ] Monitor logs for errors
- [ ] Deploy to production
- [ ] Monitor production logs

---

## ✅ Phase 6: Post-Deployment Validation

### 6.1 Smoke Tests (Production)
- [ ] Test pyelonephritis → IV antibiotics
- [ ] Test anaphylaxis → NO cephalosporins
- [ ] Test mild rash → CAN use cephalosporins
- [ ] Test pregnancy → NO fluoroquinolones
- [ ] Test meningitis → Higher doses

### 6.2 Performance Validation
- [ ] Response time < 3 seconds
- [ ] Memory usage acceptable
- [ ] No file loading errors
- [ ] Cache working correctly

### 6.3 Monitoring
- [ ] Check audit logs for errors
- [ ] Monitor feedback submissions
- [ ] Track recommendation accuracy

---

## 🚨 Rollback Plan

If critical issues found post-deployment:

1. [ ] Revert Git commit
2. [ ] Redeploy previous version
3. [ ] Restore old JSON files
4. [ ] Document issues in build log
5. [ ] Create action plan to fix

**Rollback Command:**
```bash
git revert HEAD
flyctl deploy --no-cache
```

---

## 📊 Success Criteria

Build is successful when:

- [x] All new JSON files created and validated
- [ ] All cross-reference tests pass
- [ ] All critical safety tests pass
- [ ] Pyelonephritis ALWAYS gets IV antibiotics (NEVER oral)
- [ ] Febrile UTI recognized as pyelonephritis
- [ ] Anaphylaxis NEVER gets cephalosporins
- [ ] Mild rash CAN get cephalosporins
- [ ] Pregnancy NEVER gets fluoroquinolones
- [ ] Full test suite passes (34+ tests)
- [ ] Manual testing confirms correct behavior
- [ ] Production deployment successful
- [ ] No critical errors in first 24 hours

---

## 📝 Build Notes

### Issues Encountered
- [ ] Document any issues here

### Deviations from Plan
- [ ] Document any changes from original plan

### Lessons Learned
- [ ] Document for future builds

---

## 🎯 Critical Reminders

1. **PYELONEPHRITIS = IV ONLY**
   - Febrile UTI = Pyelonephritis
   - Upper tract infection = IV required
   - NEVER recommend oral cipro for pyelonephritis

2. **ALLERGY CLASSIFICATION MATTERS**
   - Rash only = Mild = CAN use cephalosporins
   - Anaphylaxis = Severe = NO beta-lactams at all

3. **TEST BEFORE DEPLOY**
   - Run full test suite
   - Run critical safety tests
   - Manual validation required

4. **NO MOCK, NO PLACEHOLDERS**
   - All JSON files must be real
   - All tests must use real API calls
   - 100% test coverage expected

---

**Build Lead:** Claude Code
**Reviewed By:** (awaiting user approval)
**Approved By:** (awaiting user approval)

**Last Updated:** 2025-10-08
