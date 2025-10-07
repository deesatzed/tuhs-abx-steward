# Three-Step Antibiotic Recommendation System - Implementation Guide

## Overview

This document describes the implementation of a 3-step antibiotic recommendation system with human-in-the-loop validation for pilot testing.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Patient Input (Comprehensive)                 │
│  - Demographics, Weight, Renal Function, Infection, Allergies   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: Drug Selection (AI-Based)                   │
│  Input:  ABX_Selection.json + Patient Data                      │
│  Process: Agno AI Agent matches infection + allergies           │
│  Output:  Selected antibiotics (NO DOSES)                       │
│           Example: "Vancomycin + Aztreonam for bacteremia"      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 2: Dosing Calculation (Rule-Based)                │
│  Input:  ABX_Dosing.json + Selected Drugs + Patient Params      │
│  Process: Deterministic calculation based on:                   │
│           - Infection type (meningitis → higher doses)           │
│           - Renal function (CrCl categories)                     │
│           - Weight (IBW/TBW/AdjBW)                               │
│           - Loading doses (vancomycin, pip-tazo)                 │
│           - Extended infusion protocols                          │
│  Output:  Exact doses, frequencies, routes, duration            │
│           Example: "Vancomycin 25-30 mg/kg IV x1 loading,       │
│                     then 15-20 mg/kg IV q12h"                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│          STEP 3: Validation AI + Human-in-the-Loop              │
│  Input:  Combined recommendation from Steps 1 & 2               │
│  Process:                                                        │
│    3a. Validation AI reviews:                                   │
│        - Drug selection appropriateness                          │
│        - Dosing accuracy                                         │
│        - Allergy checking                                        │
│        - Contraindication detection                              │
│        - Missing information flagging                            │
│                                                                  │
│    3b. If discrepancy detected → Flag for human review          │
│                                                                  │
│    3c. Human expert reviews flagged cases:                       │
│        - Approves recommendation                                 │
│        - OR modifies and provides correction                     │
│                                                                  │
│    3d. Feedback loop:                                            │
│        - Corrections logged to improvement database              │
│        - Patterns analyzed to update Step 1 & 2 logic           │
│                                                                  │
│  Output: Validated recommendation + audit trail                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Guideline Files (Split for Maintainability)

```
ABX_Selection.json         (32KB)  - Drug selection guidelines
ABX_Dosing.json           (17KB)  - Dosing tables & renal adjustments
ABXguideInp.json          (Legacy) - Original combined file (backward compat)
```

### Code Modules

```
agno_bridge_v2.py         - Step 1: Drug selection agent
dosing_calculator.py      - Step 2: Dosing calculation (TO BE CREATED)
validation_ai.py          - Step 3: Validation AI (TO BE CREATED)
human_review_interface.py - Step 3: Human review UI (TO BE CREATED)
feedback_processor.py     - Step 3: Process corrections (TO BE CREATED)
```

---

## Step 1: Drug Selection (✅ IMPLEMENTED)

### Changes Made:
1. **Split JSON files**: Created `ABX_Selection.json` and `ABX_Dosing.json`
2. **Updated loader**: `TUHSGuidelineLoader` now reads split files with legacy fallback
3. **Modified agent instructions**:
   ```
   🎯 DRUG SELECTION ONLY (DO NOT SPECIFY DOSES):
   - Your role is to SELECT the appropriate antibiotics based on guidelines
   - DO NOT specify exact doses, frequencies, or durations
   - Output format: 'Recommended antibiotics: [Drug A] + [Drug B]'
   - Include indication (e.g., 'for meningitis')
   ```

### Output Format (Step 1):
```json
{
  "step": "drug_selection",
  "selected_antibiotics": [
    {
      "drug": "Vancomycin",
      "route": "IV",
      "reason": "MRSA coverage for bacteremia"
    },
    {
      "drug": "Aztreonam",
      "route": "IV",
      "reason": "Gram-negative coverage (severe PCN allergy)"
    }
  ],
  "indication": "bacteremia with severe penicillin allergy",
  "allergy_considerations": "Severe PCN allergy → avoided all beta-lactams",
  "confidence": 0.9,
  "requires_id_consultation": false
}
```

---

## Step 2: Dosing Calculation (⏳ TO IMPLEMENT)

### Module: `dosing_calculator.py`

```python
from typing import Dict, List, Optional
import json

class DosingCalculator:
    """
    Rule-based dosing calculator using ABX_Dosing.json
    Deterministic calculations based on patient parameters
    """

    def __init__(self, dosing_json_path: str = "ABX_Dosing.json"):
        with open(dosing_json_path, 'r') as f:
            self.dosing_data = json.load(f)
        self.dosing_table = self.dosing_data["dosing_and_renal_adjustment"]["renal_dosing_table"]

    def calculate_doses(self,
                       selected_drugs: List[Dict],
                       patient_params: Dict,
                       indication: str) -> List[Dict]:
        """
        Main dosing calculation function

        Args:
            selected_drugs: Output from Step 1 (drug names + routes)
            patient_params: Comprehensive patient data
            indication: Infection type (e.g., "meningitis", "bacteremia")

        Returns:
            List of detailed dosing recommendations
        """
        dosing_recommendations = []

        for drug_info in selected_drugs:
            drug_name = drug_info["drug"]
            route = drug_info["route"]

            # Find appropriate dosing entry
            dosing_entry = self._find_dosing_entry(drug_name, indication, route)

            if not dosing_entry:
                dosing_recommendations.append({
                    "drug": drug_name,
                    "error": f"No dosing entry found for {drug_name}",
                    "requires_manual_review": True
                })
                continue

            # Calculate patient-specific dose
            dose_calc = self._calculate_patient_specific_dose(
                dosing_entry=dosing_entry,
                patient_params=patient_params,
                indication=indication,
                drug_name=drug_name
            )

            dosing_recommendations.append(dose_calc)

        return dosing_recommendations

    def _find_dosing_entry(self, drug_name: str, indication: str, route: str) -> Optional[Dict]:
        """
        Find the most appropriate dosing table entry

        Priority:
        1. Infection-specific entry (e.g., "Vancomycin IV (Meningitis)")
        2. Loading dose entry if applicable
        3. Standard dose entry
        """
        # Normalize drug name
        drug_normalized = drug_name.lower().strip()

        # Try infection-specific first
        for entry in self.dosing_table:
            entry_drug = entry["drug"].lower()
            if drug_normalized in entry_drug and indication.lower() in entry_drug:
                return entry

        # Try standard dose
        for entry in self.dosing_table:
            entry_drug = entry["drug"].lower()
            if drug_normalized in entry_drug and "standard" in entry_drug:
                return entry

        # Fallback to any match
        for entry in self.dosing_table:
            if drug_normalized in entry["drug"].lower():
                return entry

        return None

    def _calculate_patient_specific_dose(self,
                                         dosing_entry: Dict,
                                         patient_params: Dict,
                                         indication: str,
                                         drug_name: str) -> Dict:
        """Calculate patient-specific dose based on all parameters"""

        # Extract patient parameters
        age = patient_params.get("age")
        weight_data = patient_params.get("weight", {})
        renal_data = patient_params.get("renal_function", {})

        # Determine weight to use
        weight_kg = self._determine_weight_to_use(weight_data, drug_name)

        # Determine renal category
        renal_category = self._determine_renal_category(renal_data)

        # Get base dose from dosing table
        base_dose = dosing_entry.get(renal_category, dosing_entry.get("crcl_gt_50"))

        # Check if loading dose needed
        loading_dose = None
        if self._requires_loading_dose(drug_name, indication, patient_params):
            loading_dose = dosing_entry.get("ed_once_dose")

        # Parse and calculate dose ranges
        dose_recommendation = self._format_dose_recommendation(
            drug_name=drug_name,
            base_dose=base_dose,
            loading_dose=loading_dose,
            weight_kg=weight_kg,
            indication=indication,
            renal_category=renal_category,
            patient_params=patient_params
        )

        return dose_recommendation

    def _determine_weight_to_use(self, weight_data: Dict, drug_name: str) -> float:
        """
        Determine which weight to use (IBW, TBW, or AdjBW)

        Rules:
        - If TBW < IBW: use TBW
        - If TBW > 120% IBW: use AdjBW
        - Otherwise: use IBW
        - Special case: If BMI ≥35 and drug is Acyclovir: use AdjBW
        """
        tbw = weight_data.get("total_body_weight_kg")
        ibw = weight_data.get("ideal_body_weight_kg", tbw)
        adjbw = weight_data.get("adjusted_body_weight_kg", tbw)
        bmi = weight_data.get("bmi")

        # Special case for Acyclovir
        if "acyclovir" in drug_name.lower() and bmi and bmi >= 35:
            return adjbw

        # General rules
        if tbw < ibw:
            return tbw
        elif tbw > (1.2 * ibw):
            return adjbw
        else:
            return ibw

    def _determine_renal_category(self, renal_data: Dict) -> str:
        """
        Map renal function to dosing category

        Categories:
        - crcl_gt_50: CrCl > 50
        - crcl_50_30: CrCl 30-50
        - crcl_29_10: CrCl 10-29
        - crcl_lt_10_no_hd: CrCl < 10, not on HD
        - hd: Hemodialysis
        - cvvhdf: Continuous venovenous hemodiafiltration
        """
        dialysis_info = renal_data.get("renal_replacement", {})

        if dialysis_info.get("on_dialysis"):
            dialysis_type = dialysis_info.get("dialysis_type")
            if dialysis_type == "HD":
                return "hd"
            elif dialysis_type == "CVVHDF":
                return "cvvhdf"

        crcl = renal_data.get("creatinine_clearance", 100)

        if crcl > 50:
            return "crcl_gt_50"
        elif 30 <= crcl <= 50:
            return "crcl_50_30"
        elif 10 <= crcl <= 29:
            return "crcl_29_10"
        else:
            return "crcl_lt_10_no_hd"

    def _requires_loading_dose(self, drug_name: str, indication: str, patient_params: Dict) -> bool:
        """
        Determine if loading dose is required

        Criteria:
        - Vancomycin + Meningitis: Always
        - Vancomycin + Severe sepsis: Usually
        - Piperacillin-tazobactam + Extended infusion protocol: Yes
        - Cefepime + Intensive dosing: Yes
        """
        drug_lower = drug_name.lower()
        indication_lower = indication.lower()

        clinical_status = patient_params.get("clinical_status", {})

        if "vancomycin" in drug_lower:
            if "meningitis" in indication_lower:
                return True
            if clinical_status.get("septic_shock"):
                return True

        if "piperacillin" in drug_lower or "pip" in drug_lower:
            # Check if extended infusion protocol should be used
            if patient_params.get("location") == "ICU":
                return True

        return False

    def _format_dose_recommendation(self,
                                    drug_name: str,
                                    base_dose: str,
                                    loading_dose: Optional[str],
                                    weight_kg: float,
                                    indication: str,
                                    renal_category: str,
                                    patient_params: Dict) -> Dict:
        """Format the final dose recommendation with all details"""

        recommendation = {
            "drug": drug_name,
            "indication": indication,
            "weight_used_kg": weight_kg,
            "renal_category": renal_category,
            "renal_adjustment_applied": True
        }

        # Add loading dose if applicable
        if loading_dose:
            recommendation["loading_dose"] = {
                "dose": loading_dose,
                "calculated_dose_range": self._calculate_range(loading_dose, weight_kg),
                "administration": "Give as first dose",
                "infusion_time": self._get_infusion_time(drug_name, "loading")
            }

        # Add maintenance dose
        recommendation["maintenance_dose"] = {
            "dose": base_dose,
            "calculated_dose_range": self._calculate_range(base_dose, weight_kg),
            "administration": "Maintenance regimen",
            "infusion_time": self._get_infusion_time(drug_name, "maintenance")
        }

        # Add monitoring parameters
        recommendation["monitoring"] = self._get_monitoring_parameters(drug_name, indication)

        # Add duration guidance
        recommendation["duration"] = self._get_duration_guidance(indication)

        # Add special considerations
        recommendation["special_considerations"] = self._get_special_considerations(
            drug_name, patient_params, indication
        )

        return recommendation

    def _calculate_range(self, dose_string: str, weight_kg: float) -> str:
        """Calculate actual dose range from dose string like '15-20 mg/kg'"""
        import re

        # Extract numbers
        numbers = re.findall(r'\d+(?:\.\d+)?', dose_string)

        if 'mg/kg' in dose_string and len(numbers) >= 2:
            low = float(numbers[0]) * weight_kg
            high = float(numbers[1]) * weight_kg
            return f"{low:.0f}-{high:.0f} mg"
        elif 'mg/kg' in dose_string and len(numbers) == 1:
            dose = float(numbers[0]) * weight_kg
            return f"{dose:.0f} mg"
        else:
            # Fixed dose, return as-is
            return dose_string

    def _get_infusion_time(self, drug_name: str, dose_type: str) -> str:
        """Get recommended infusion time"""
        drug_lower = drug_name.lower()

        if "vancomycin" in drug_lower:
            return "Over 1-2 hours (not faster than 10 mg/min)"

        if "cefepime" in drug_lower or "ceftriaxone" in drug_lower:
            return "Over 30 minutes"

        if "piperacillin" in drug_lower:
            if dose_type == "loading":
                return "Over 30 minutes"
            else:
                return "Extended infusion over 4 hours (if using extended protocol)"

        return "Per standard protocol"

    def _get_monitoring_parameters(self, drug_name: str, indication: str) -> List[str]:
        """Get monitoring parameters for the drug"""
        drug_lower = drug_name.lower()
        monitoring = []

        if "vancomycin" in drug_lower:
            monitoring.append("Trough levels before 4th dose")
            if "meningitis" in indication.lower():
                monitoring.append("Target trough: 15-20 mcg/mL")
            else:
                monitoring.append("Target trough: 10-20 mcg/mL")
            monitoring.append("Consider AUC-guided dosing")
            monitoring.append("Monitor renal function (SCr, BUN)")

        if "aminoglycoside" in drug_lower or "gentamicin" in drug_lower or "tobramycin" in drug_lower:
            monitoring.append("Peak and trough levels")
            monitoring.append("Monitor renal function and hearing")

        if any(drug in drug_lower for drug in ["cefepime", "piperacillin", "meropenem"]):
            monitoring.append("Monitor renal function for dose adjustment")
            monitoring.append("Monitor for neurological side effects if high dose")

        monitoring.append("Clinical response and signs of improvement")
        monitoring.append("Culture results and sensitivities")

        return monitoring

    def _get_duration_guidance(self, indication: str) -> str:
        """Get duration guidance based on indication"""
        indication_lower = indication.lower()

        duration_map = {
            "meningitis": "Typically 10-14 days (organism-dependent, may be longer for certain pathogens)",
            "bacteremia": "Typically 7-14 days (depends on source control and organism)",
            "pneumonia": "Typically 5-7 days for CAP, 7-14 days for HAP/VAP",
            "pyelonephritis": "Typically 7-14 days",
            "cystitis": "Typically 1-5 days (agent-dependent)",
            "ssti": "Typically 5-10 days (severity-dependent)",
            "intra_abdominal": "Typically 4-7 days with adequate source control"
        }

        for key, duration in duration_map.items():
            if key in indication_lower:
                return duration

        return "Duration varies by clinical response, source control, and organism. Reassess at 48-72 hours."

    def _get_special_considerations(self, drug_name: str, patient_params: Dict, indication: str) -> List[str]:
        """Get special considerations based on patient and drug"""
        considerations = []

        # Recent surgery
        recent_surgery = patient_params.get("recent_surgery", {})
        if recent_surgery.get("had_surgery"):
            considerations.append(f"Recent surgery noted - monitor for surgical site complications")

        # TPN
        if recent_surgery.get("on_tpn"):
            considerations.append("Patient on TPN - consider fungal coverage if prolonged")

        # Septic shock
        clinical_status = patient_params.get("clinical_status", {})
        if clinical_status.get("septic_shock"):
            considerations.append("Septic shock present - ensure prompt administration within 1 hour")

        # Renal impairment
        renal_data = patient_params.get("renal_function", {})
        crcl = renal_data.get("creatinine_clearance", 100)
        if crcl < 30:
            considerations.append("Significant renal impairment - close monitoring and dose adjustments required")

        # Drug-specific
        drug_lower = drug_name.lower()
        if "vancomycin" in drug_lower and "meningitis" in indication.lower():
            considerations.append("For meningitis: Consider adding rifampin if organism is susceptible")

        return considerations
```

### Output Format (Step 2):
```json
{
  "step": "dosing_calculation",
  "dosing_recommendations": [
    {
      "drug": "Vancomycin",
      "indication": "bacteremia with MRSA coverage",
      "weight_used_kg": 68,
      "renal_category": "crcl_50_30",
      "renal_adjustment_applied": true,
      "loading_dose": {
        "dose": "25-30 mg/kg IV",
        "calculated_dose_range": "1700-2040 mg",
        "administration": "Give as first dose",
        "infusion_time": "Over 1-2 hours (not faster than 10 mg/min)"
      },
      "maintenance_dose": {
        "dose": "15-20 mg/kg IV q12h",
        "calculated_dose_range": "1020-1360 mg IV q12h",
        "administration": "Maintenance regimen",
        "infusion_time": "Over 1-2 hours"
      },
      "monitoring": [
        "Trough levels before 4th dose",
        "Target trough: 10-20 mcg/mL",
        "Consider AUC-guided dosing",
        "Monitor renal function (SCr, BUN)"
      ],
      "duration": "Typically 7-14 days (depends on source control and organism)",
      "special_considerations": [
        "Recent surgery noted - monitor for surgical site complications",
        "Patient on TPN - consider fungal coverage if prolonged"
      ]
    },
    {
      "drug": "Aztreonam",
      "indication": "Gram-negative coverage (severe PCN allergy)",
      "weight_used_kg": 68,
      "renal_category": "crcl_50_30",
      "renal_adjustment_applied": true,
      "maintenance_dose": {
        "dose": "1-2g IV q8h",
        "calculated_dose_range": "1000-2000 mg IV q8h",
        "administration": "Standard regimen",
        "infusion_time": "Over 30 minutes"
      },
      "monitoring": [
        "Monitor renal function for dose adjustment",
        "Clinical response and signs of improvement",
        "Culture results and sensitivities"
      ],
      "duration": "Typically 7-14 days (depends on source control and organism)"
    }
  ]
}
```

---

## Step 3: Validation AI + Human-in-the-Loop (⏳ TO IMPLEMENT)

### Module: `validation_ai.py`

```python
from typing import Dict, List, Tuple
from agno import Agent, OpenAIChat
import json

class ValidationAI:
    """
    AI-powered validation of antibiotic recommendations
    Checks for errors, contraindications, and missing information
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.validator_agent = self._create_validator_agent()

    def _create_validator_agent(self) -> Agent:
        """Create specialized validation agent"""

        validation_instructions = [
            "You are an expert infectious disease pharmacist reviewing antibiotic recommendations.",
            "Your role is to validate recommendations for:",
            "1. Drug selection appropriateness",
            "2. Dosing accuracy",
            "3. Allergy checking",
            "4. Contraindication detection",
            "5. Missing information",
            "",
            "VALIDATION CHECKLIST:",
            "✅ Appropriate drug for infection type",
            "✅ Allergy-safe (no contraindicated drugs)",
            "✅ Renal adjustment correct",
            "✅ Loading dose given when needed",
            "✅ Monitoring parameters included",
            "✅ Duration appropriate",
            "",
            "COMMON ERRORS TO CATCH:",
            "❌ Cephalosporins for severe PCN allergy (anaphylaxis)",
            "❌ Fluoroquinolones for pyelonephritis when better options exist",
            "❌ Missing loading doses (vancomycin for meningitis)",
            "❌ Wrong dose for indication (meningitis needs higher doses)",
            "❌ Inadequate renal adjustment",
            "",
            "OUTPUT FORMAT:",
            "If recommendation is CORRECT:",
            "  - status: 'APPROVED'",
            "  - confidence: 0.9-1.0",
            "  - notes: Brief approval statement",
            "",
            "If DISCREPANCY found:",
            "  - status: 'REQUIRES_REVIEW'",
            "  - confidence: 0.0-0.6",
            "  - issues: List of specific problems",
            "  - suggested_corrections: What should be changed",
            "  - severity: 'CRITICAL' | 'MODERATE' | 'MINOR'"
        ]

        model = OpenAIChat(
            id="gpt-4o-mini",
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0  # Deterministic validation
        )

        return Agent(
            model=model,
            name="TUHS_Validation_Expert",
            description="Validates antibiotic recommendations for safety and accuracy",
            instructions=validation_instructions
        )

    async def validate_recommendation(self,
                                     drug_selection: Dict,
                                     dosing_calculation: Dict,
                                     patient_params: Dict) -> Dict:
        """
        Validate complete recommendation

        Returns:
            {
                "status": "APPROVED" | "REQUIRES_REVIEW",
                "confidence": 0.0-1.0,
                "issues": [...],
                "suggested_corrections": [...],
                "severity": "CRITICAL" | "MODERATE" | "MINOR" | null,
                "requires_human_review": bool
            }
        """

        # Build validation query
        validation_query = self._build_validation_query(
            drug_selection, dosing_calculation, patient_params
        )

        # Run validation agent
        validation_result = await self.validator_agent.arun(validation_query)
        result_text = validation_result.content if hasattr(validation_result, 'content') else str(validation_result)

        # Parse validation result
        parsed_result = self._parse_validation_result(result_text)

        # Determine if human review required
        parsed_result["requires_human_review"] = (
            parsed_result["status"] == "REQUIRES_REVIEW" or
            parsed_result["confidence"] < 0.7
        )

        return parsed_result

    def _build_validation_query(self,
                                drug_selection: Dict,
                                dosing_calculation: Dict,
                                patient_params: Dict) -> str:
        """Build query for validation agent"""

        query = f"""
VALIDATE THE FOLLOWING ANTIBIOTIC RECOMMENDATION:

PATIENT INFORMATION:
- Age: {patient_params.get('age')}
- Gender: {patient_params.get('gender')}
- Weight: {patient_params.get('weight', {}).get('total_body_weight_kg')} kg
- CrCl: {patient_params.get('renal_function', {}).get('creatinine_clearance')} mL/min
- Allergies: {json.dumps(patient_params.get('allergies', {}), indent=2)}
- Infection: {patient_params.get('infection', {}).get('type')}
- Location: {patient_params.get('location')}

DRUG SELECTION (Step 1):
{json.dumps(drug_selection, indent=2)}

DOSING CALCULATION (Step 2):
{json.dumps(dosing_calculation, indent=2)}

Please validate this recommendation against TUHS guidelines and respond in JSON format:
{{
  "status": "APPROVED" or "REQUIRES_REVIEW",
  "confidence": 0.0-1.0,
  "issues": ["list of issues if any"],
  "suggested_corrections": ["list of corrections if needed"],
  "severity": "CRITICAL" or "MODERATE" or "MINOR" or null,
  "notes": "Brief explanation"
}}
"""
        return query

    def _parse_validation_result(self, result_text: str) -> Dict:
        """Parse validation result from AI response"""
        import re

        # Try to extract JSON
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        # Fallback: basic parsing
        if any(word in result_text.lower() for word in ['error', 'incorrect', 'contraindicated', 'problem']):
            return {
                "status": "REQUIRES_REVIEW",
                "confidence": 0.5,
                "issues": ["Validation agent flagged concerns - see notes"],
                "suggested_corrections": [],
                "severity": "MODERATE",
                "notes": result_text
            }
        else:
            return {
                "status": "APPROVED",
                "confidence": 0.9,
                "issues": [],
                "suggested_corrections": [],
                "severity": null,
                "notes": result_text
            }
```

### Module: `human_review_interface.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
from datetime import datetime

router = APIRouter(prefix="/api/review", tags=["human_review"])

class ReviewCase(BaseModel):
    case_id: str
    patient_data: Dict
    drug_selection: Dict
    dosing_calculation: Dict
    validation_result: Dict
    flagged_at: str

class ReviewDecision(BaseModel):
    case_id: str
    reviewer_id: str
    decision: str  # "APPROVE" | "MODIFY" | "REJECT"
    corrections: Optional[Dict] = None
    notes: str

# In-memory store for pilot (replace with database)
pending_reviews = {}
review_history = []

@router.get("/pending")
async def get_pending_reviews():
    """Get all cases awaiting human review"""
    return {
        "count": len(pending_reviews),
        "cases": list(pending_reviews.values())
    }

@router.get("/case/{case_id}")
async def get_review_case(case_id: str):
    """Get specific case for review"""
    if case_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Case not found")

    return pending_reviews[case_id]

@router.post("/submit")
async def submit_review(review: ReviewDecision):
    """Submit human review decision"""

    if review.case_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Case not found")

    case = pending_reviews[review.case_id]

    # Record decision
    decision_record = {
        "case_id": review.case_id,
        "reviewer_id": review.reviewer_id,
        "decision": review.decision,
        "corrections": review.corrections,
        "notes": review.notes,
        "reviewed_at": datetime.now().isoformat(),
        "original_recommendation": {
            "drug_selection": case["drug_selection"],
            "dosing_calculation": case["dosing_calculation"]
        }
    }

    review_history.append(decision_record)

    # Remove from pending
    del pending_reviews[review.case_id]

    # If corrections provided, process for feedback loop
    if review.corrections and review.decision == "MODIFY":
        await process_correction_feedback(decision_record)

    return {
        "status": "success",
        "message": "Review submitted",
        "decision_record": decision_record
    }

@router.get("/history")
async def get_review_history(limit: int = 100):
    """Get review history for analysis"""
    return {
        "count": len(review_history),
        "reviews": review_history[-limit:]
    }

@router.get("/stats")
async def get_review_stats():
    """Get review statistics"""

    if not review_history:
        return {"message": "No reviews yet"}

    total = len(review_history)
    approved = sum(1 for r in review_history if r["decision"] == "APPROVE")
    modified = sum(1 for r in review_history if r["decision"] == "MODIFY")
    rejected = sum(1 for r in review_history if r["decision"] == "REJECT")

    return {
        "total_reviews": total,
        "approved": approved,
        "modified": modified,
        "rejected": rejected,
        "approval_rate": approved / total if total > 0 else 0,
        "modification_rate": modified / total if total > 0 else 0
    }

async def process_correction_feedback(decision_record: Dict):
    """
    Process corrections to improve Steps 1 & 2

    This function analyzes corrections and:
    1. Identifies patterns in errors
    2. Updates instruction prompts if needed
    3. Logs for manual guideline updates
    """

    # Log correction for analysis
    with open("logs/corrections_feedback.jsonl", "a") as f:
        f.write(json.dumps(decision_record) + "\n")

    # TODO: Implement pattern analysis and automated improvements
    # For now, just logging for manual review
```

---

## Workflow Integration

### Updated `fastapi_server.py` endpoint:

```python
@app.post("/api/recommendation_v2")
async def get_recommendation_v2(patient_data: PatientDataV2):
    """
    V2 endpoint with 3-step process and validation
    """
    request_id = f"req_{int(time.time() * 1000)}_{os.urandom(4).hex()}"

    try:
        # STEP 1: Drug Selection
        bridge = get_bridge()
        drug_selection = await bridge.process_request(patient_data.model_dump())

        # STEP 2: Dosing Calculation
        from dosing_calculator import DosingCalculator
        dosing_calc = DosingCalculator()
        dosing_recommendations = dosing_calc.calculate_doses(
            selected_drugs=drug_selection["selected_antibiotics"],
            patient_params=patient_data.model_dump(),
            indication=drug_selection["indication"]
        )

        # STEP 3: Validation
        from validation_ai import ValidationAI
        validator = ValidationAI(api_key=os.getenv("OPENROUTER_API_KEY"))
        validation_result = await validator.validate_recommendation(
            drug_selection=drug_selection,
            dosing_calculation={"dosing_recommendations": dosing_recommendations},
            patient_params=patient_data.model_dump()
        )

        # If requires human review, add to queue
        if validation_result["requires_human_review"]:
            from human_review_interface import pending_reviews
            pending_reviews[request_id] = {
                "case_id": request_id,
                "patient_data": patient_data.model_dump(),
                "drug_selection": drug_selection,
                "dosing_calculation": {"dosing_recommendations": dosing_recommendations},
                "validation_result": validation_result,
                "flagged_at": datetime.now().isoformat()
            }

        # Return combined result
        return {
            "request_id": request_id,
            "step1_drug_selection": drug_selection,
            "step2_dosing": {"dosing_recommendations": dosing_recommendations},
            "step3_validation": validation_result,
            "requires_human_review": validation_result["requires_human_review"],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Deployment Plan

### Phase 1: Implement Step 2 (Dosing Calculator)
- ✅ Split JSON files (DONE)
- ⏳ Create `dosing_calculator.py`
- ⏳ Test dosing calculations
- ⏳ Integrate with FastAPI

### Phase 2: Implement Step 3 (Validation)
- ⏳ Create `validation_ai.py`
- ⏳ Create `human_review_interface.py`
- ⏳ Build simple review UI
- ⏳ Set up feedback logging

### Phase 3: Pilot Testing
- ⏳ Deploy with human reviewers
- ⏳ Collect 100+ reviewed cases
- ⏳ Analyze patterns
- ⏳ Update guidelines based on feedback

### Phase 4: Continuous Improvement
- ⏳ Automate pattern recognition
- ⏳ Update Step 1 instructions based on common errors
- ⏳ Refine Step 2 dosing rules
- ⏳ Reduce human review rate as accuracy improves

---

## Success Metrics

### Pilot Phase (First 100 Cases):
- Target: ≥80% approval rate without modifications
- Target: ≥95% safety (no critical errors)
- Target: 100% of flagged cases reviewed within 24 hours

### Post-Pilot (Next 1000 Cases):
- Target: ≥90% approval rate
- Target: ≥98% safety
- Target: <10% requiring human review

---

## Next Steps

1. ✅ **Complete**: Split JSON files and update loader
2. **In Progress**: Document 3-step architecture
3. **To Do**: Implement `dosing_calculator.py`
4. **To Do**: Implement `validation_ai.py`
5. **To Do**: Implement `human_review_interface.py`
6. **To Do**: Deploy and begin pilot testing

