# Frontend Error Reporting - Test Guide

**Date**: 2025-10-08
**Purpose**: Test the error reporting UI integrated into Alpine.js frontend

---

## Prerequisites

1. FastAPI server running on port 8080
2. Frontend accessible at http://localhost:8080/
3. Browser with JavaScript enabled

---

## Test 1: Access Frontend

### Steps
1. Start the server:
```bash
python fastapi_server.py
```

2. Open browser to http://localhost:8080/

### Expected Result
- ✅ Frontend loads successfully
- ✅ "TUHS Antibiotic Steward" header visible
- ✅ Form sections visible on left
- ✅ No errors in browser console

---

## Test 2: Generate a Recommendation (Required First)

### Steps
1. Fill in patient data:
   - Age: 55
   - Gender: Male
   - GFR: 60
   - Location: Ward (default)
   - Infection Type: Select "UTI/Pyelonephritis"
   - Allergies: Check "Penicillin (anaphylaxis)"

2. Click "Generate Recommendation" button

### Expected Result
- ✅ Loading spinner appears
- ✅ Recommendation displays in right panel
- ✅ "Flag Error" button appears (yellow/warning color)
- ✅ "Search Evidence" button visible

---

## Test 3: Click Flag Error (Without Recommendation)

### Steps
1. Refresh page (no recommendation loaded)
2. Try clicking "Flag Error" button (if visible before generating)

### Expected Result
- ✅ Alert message: "Please generate a recommendation first before reporting an error."
- ✅ Modal does NOT open

---

## Test 4: Open Error Report Modal

### Steps
1. Generate a recommendation (Test 2)
2. Click "Flag Error" button

### Expected Result
- ✅ Modal opens with title "Report Recommendation Error"
- ✅ All form fields visible:
  - Error Type dropdown
  - Severity dropdown
  - Error Description textarea
  - Expected Recommendation textarea
  - Reporter Name input (optional)
- ✅ Cancel button visible
- ✅ Submit button visible (disabled)

---

## Test 5: Modal Form Validation

### Steps
1. Open error report modal
2. Try clicking "Submit Error Report" button (without filling fields)

### Expected Result
- ✅ Button is disabled (grayed out)
- ✅ Nothing happens when clicked

### Steps (Continued)
3. Fill only Error Type (select "Contraindicated Drug Given")
4. Try clicking Submit

### Expected Result
- ✅ Button still disabled

### Steps (Continued)
5. Fill Error Description: "Gave ceftriaxone to severe PCN allergy"
6. Fill Expected Recommendation: "Should give aztreonam"
7. Check Submit button

### Expected Result
- ✅ Button is now ENABLED (not grayed out)

---

## Test 6: Submit Error Report (Complete)

### Steps
1. Open error report modal
2. Fill all required fields:
   - Error Type: "Contraindicated Drug Given"
   - Severity: "High"
   - Error Description: "System recommended ceftriaxone to patient with documented PCN anaphylaxis"
   - Expected Recommendation: "Should have recommended aztreonam instead due to severe PCN allergy"
   - Reporter Name: "Test Pharmacist" (optional)
3. Click "Submit Error Report"

### Expected Result
- ✅ Loading spinner appears on button
- ✅ Button shows loading spinner
- ✅ Browser console shows: "Submitting error report: {payload}"
- ✅ Success alert appears with Error ID (e.g., "ERR-20251008-xxxxxxxx")
- ✅ Modal closes automatically
- ✅ Form fields reset

### Verify Backend
```bash
# Check error report file
cat logs/error_reports/$(date +%Y-%m-%d).jsonl | jq
```

**Expected**:
- ✅ New error report saved with correct data
- ✅ error_id matches the one shown in alert
- ✅ status: "new"
- ✅ All fields populated correctly

---

## Test 7: Cancel Error Report

### Steps
1. Open error report modal
2. Fill some fields (partially)
3. Click "Cancel" button

### Expected Result
- ✅ Modal closes
- ✅ Form fields reset
- ✅ No error report submitted

---

## Test 8: Test All Error Types

### Steps
For each error type, submit a report:

1. **Contraindicated Drug Given**
   - Description: "Gave beta-lactam to severe PCN allergy"
   - Expected: "Aztreonam"

2. **Wrong Drug Selected**
   - Description: "Gave ceftriaxone for MRSA bacteremia"
   - Expected: "Vancomycin"

3. **Wrong Dose/Frequency**
   - Description: "Vancomycin 1g q12h for 45kg patient"
   - Expected: "Weight-based dosing: 15mg/kg"

4. **Missed Allergy**
   - Description: "Allergy field ignored"
   - Expected: "Check allergy before recommending"

5. **Missed Interaction**
   - Description: "Drug interaction not flagged"
   - Expected: "Check for interactions"

6. **Wrong Route (IV vs PO)**
   - Description: "Recommended PO for severe infection"
   - Expected: "IV therapy required"

7. **Other**
   - Description: "General issue"
   - Expected: "Various"

### Expected Result
- ✅ All 7 error types submit successfully
- ✅ Each gets unique error ID
- ✅ All saved to JSONL file

---

## Test 9: Test All Severity Levels

### Steps
Submit 4 error reports with different severities:

1. **Low Severity**
   - Type: Wrong dose
   - Description: "Minor dose optimization possible"

2. **Medium Severity**
   - Type: Wrong drug
   - Description: "Suboptimal drug choice"

3. **High Severity**
   - Type: Contraindicated
   - Description: "Gave contraindicated drug"

4. **Critical Severity**
   - Type: Contraindicated
   - Description: "Life-threatening contraindication"

### Expected Result
- ✅ All 4 submit successfully
- ✅ Critical error logs "🚨 CRITICAL ERROR REPORT" in server console
- ✅ All saved with correct severity level

---

## Test 10: Multiple Recommendations Test

### Steps
1. Generate recommendation #1 (UTI + PCN allergy)
2. Flag error for recommendation #1
3. Generate recommendation #2 (Pneumonia, no allergy)
4. Flag error for recommendation #2

### Expected Result
- ✅ Both error reports save correctly
- ✅ Each captures the correct patient data
- ✅ Each captures the correct recommendation given
- ✅ No data mixing between reports

---

## Test 11: Browser Console Checks

### Steps
1. Open browser DevTools (F12)
2. Go to Console tab
3. Submit an error report
4. Watch console output

### Expected Result
- ✅ "Submitting error report:" with full payload
- ✅ "Error report submitted:" with response (error_id)
- ✅ No JavaScript errors
- ✅ No network errors (check Network tab)

---

## Test 12: Network Request Validation

### Steps
1. Open browser DevTools (F12)
2. Go to Network tab
3. Submit an error report
4. Find the POST request to `/api/error-report`

### Expected Result
- ✅ Request Method: POST
- ✅ Status Code: 200 OK
- ✅ Request Headers: Content-Type: application/json
- ✅ Request Payload: Complete JSON structure
- ✅ Response: { success: true, error_id: "...", message: "..." }

---

## Test 13: Modal UI Responsiveness

### Steps
1. Resize browser window (mobile, tablet, desktop sizes)
2. Open error report modal at each size
3. Try scrolling within modal

### Expected Result
- ✅ Modal adapts to screen size
- ✅ All fields accessible on mobile
- ✅ Text readable on small screens
- ✅ Buttons accessible
- ✅ Modal scrolls if content overflows

---

## Test 14: Error Handling

### Steps
1. Stop the FastAPI server
2. Try to submit error report

### Expected Result
- ✅ Error alert shows: "Failed to submit error report: [error message]"
- ✅ Modal stays open
- ✅ Form data preserved
- ✅ User can fix issue and retry

### Steps (Continued)
3. Restart server
4. Retry submission

### Expected Result
- ✅ Submission succeeds after server restart

---

## Test 15: De-identification Check

### Steps
1. Generate recommendation with:
   - Age: 67
   - Include allergies: "Penicillin (rash)"
   - Include other clinical data
2. Submit error report
3. Check saved error report file

### Expected Result
- ✅ Age saved (allowed)
- ✅ Gender saved (allowed)
- ✅ GFR saved (allowed)
- ✅ Allergies saved (de-identified - no patient name)
- ✅ NO patient name in file
- ✅ NO MRN in file
- ✅ NO date of birth in file

---

## Common Issues & Solutions

### Issue: Modal doesn't open
**Solution**: Check browser console for JavaScript errors. Ensure Alpine.js loaded correctly.

### Issue: Submit button always disabled
**Solution**: Check that all 3 required fields are filled (error_type, error_description, expected_recommendation).

### Issue: Error "Failed to submit"
**Solution**: Ensure FastAPI server is running on port 8080. Check Network tab for errors.

### Issue: Modal doesn't close after submit
**Solution**: Check browser console for errors. Verify API returned success response.

---

## Success Criteria

- [ ] Frontend loads without errors
- [ ] Flag Error button appears after generating recommendation
- [ ] Modal opens and displays all fields
- [ ] Form validation works (required fields)
- [ ] Error reports submit successfully
- [ ] Success message displays with error ID
- [ ] Modal closes and resets after submit
- [ ] Error reports saved to backend file
- [ ] All error types can be submitted
- [ ] All severity levels work correctly
- [ ] Browser console shows no errors
- [ ] Network requests complete successfully

---

## Next Steps

After frontend testing passes:
1. Test with real pilot pharmacists
2. Gather feedback on UI/UX
3. Proceed to Phase 2: Automated verification
4. Build admin dashboard to view reports

---

**Test Status**: Ready for testing
**Estimated Time**: 30-45 minutes
**Files to Check**: logs/error_reports/YYYY-MM-DD.jsonl
