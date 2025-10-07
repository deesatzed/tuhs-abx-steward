# Antibiotic Dosing Architecture - Two-Step Process

## Problem Statement

The current system combines drug selection and dosing calculation in a single AI call, leading to:
1. **Incorrect dosing** - AI uses generic doses instead of infection-specific doses (e.g., meningitis requires higher doses)
2. **Missing loading doses** - Vancomycin loading dose not recommended for meningitis
3. **Renal adjustment errors** - Doses based only on GFR, ignoring recent surgery, dialysis timing, or weight-based calculations
4. **Incomplete decision factors** - Not capturing all variables needed for proper dosing

## Solution: Two-Step Process

### **STEP 1: Drug Selection** (AI-based)
**Input**: Patient demographics, infection type, allergies, culture results
**Output**: Selected antibiotic(s) with indication
**Example**: "Vancomycin + Ceftriaxone for meningitis"

### **STEP 2: Dosing Calculation** (Rule-based)
**Input**: Selected drug(s), patient parameters, infection indication
**Output**: Specific dose, frequency, route, duration
**Example**: "Vancomycin 25-30 mg/kg IV x1 loading dose, then 15-20 mg/kg q8-12h + Ceftriaxone 2g IV q12h (meningitis dose)"

---

## Dosing Decision Factors

### Patient-Specific Factors
```json
{
  "patient_id": "optional_identifier",
  "age": 88,
  "gender": "male",

  "weight": {
    "total_body_weight_kg": 70,
    "ideal_body_weight_kg": 65,
    "adjusted_body_weight_kg": 67.5,
    "bmi": 24.5,
    "weight_to_use": "IBW"  // IBW | TBW | AdjBW (auto-calculated if not provided)
  },

  "renal_function": {
    "serum_creatinine": 1.5,
    "creatinine_clearance": 44,  // Cockcroft-Gault formula
    "egfr": 45,  // Often not used for dosing
    "renal_replacement": {
      "on_dialysis": false,
      "dialysis_type": null,  // "HD" | "PD" | "CVVHDF" | null
      "last_dialysis": null,  // ISO datetime if HD
      "dialysis_schedule": null  // "MWF" | "TThSa" | "daily" | null
    }
  },

  "hepatic_function": {
    "child_pugh_score": null,  // A | B | C | null
    "alt": null,
    "ast": null,
    "bilirubin": null
  },

  "recent_surgery": {
    "had_surgery": false,
    "surgery_date": null,  // ISO datetime
    "surgery_type": null,  // e.g., "abdominal", "cardiac", "orthopedic"
    "on_tpn": false  // Total parenteral nutrition
  },

  "location": "Ward",  // "Ward" | "ICU" | "ED"
  "septic_shock": false,
  "immunocompromised": false,
  "pregnant": false,
  "breastfeeding": false
}
```

### Infection-Specific Factors
```json
{
  "infection": {
    "type": "bacteremia",  // pneumonia | uti | meningitis | ssti | etc.
    "severity": "severe",  // mild | moderate | severe
    "source": "unknown",  // If sepsis: abdomen | lung | urinary | skin | unknown
    "onset": "hospital_acquired",  // community | hospital_acquired | healthcare_associated
    "days_hospitalized": 3  // Used to determine if >48hrs
  }
}
```

### Allergy Information
```json
{
  "allergies": {
    "penicillin": {
      "has_allergy": true,
      "severity": "severe",  // null | "mild" | "moderate" | "severe"
      "reaction_type": "anaphylaxis",  // "rash" | "hives" | "itching" | "anaphylaxis" | "sjs" | "dress" | "angioedema"
      "reaction_date": null
    },
    "cephalosporin": {
      "has_allergy": false,
      "severity": null,
      "reaction_type": null
    },
    "sulfa": {
      "has_allergy": false,
      "severity": null,
      "reaction_type": null
    },
    "fluoroquinolone": {
      "has_allergy": false,
      "severity": null,
      "reaction_type": null
    },
    "other": []  // List of other drug allergies
  }
}
```

### Microbiology Data
```json
{
  "microbiology": {
    "culture_results": {
      "status": "pending",  // "pending" | "positive" | "negative" | "contaminated"
      "organism": null,  // e.g., "MRSA", "E. coli ESBL", "Pseudomonas aeruginosa"
      "sensitivities": {},  // {drug_name: "S" | "I" | "R"}
      "mic_values": {}  // {drug_name: 0.5} for MIC-specific dosing
    },

    "prior_cultures_6mo": {
      "has_mdro": false,  // Multi-drug resistant organism
      "organisms": [],  // ["MRSA", "VRE", "ESBL E. coli"]
      "last_culture_date": null
    },

    "colonization": {
      "mrsa_nares": null,  // true | false | null (not tested)
      "vre_rectal": null,
      "other": []
    }
  }
}
```

### Current Medications
```json
{
  "current_medications": {
    "antibiotics": {
      "outpatient": [],  // List of antibiotics taken before admission
      "inpatient": [
        {
          "drug": "ceftriaxone",
          "dose": "1g",
          "frequency": "q24h",
          "route": "IV",
          "start_date": "2025-10-04",
          "days_on_therapy": 2
        }
      ]
    },
    "immunosuppressants": [],
    "chemotherapy": false,
    "corticosteroids": false
  }
}
```

---

## Dosing Table Structure from ABXguideInp.json

```json
{
  "drug": "Vancomycin IV (Standard dose: 15-20 mg/kg)",
  "ed_once_dose": "25-30 mg/kg",  // Loading dose
  "crcl_gt_50": "15-20 mg/kg q8-12h",
  "crcl_50_30": "15-20 mg/kg q12-24h",
  "crcl_29_10": "15-20 mg/kg q24-48h",
  "crcl_lt_10_no_hd": "15-20 mg/kg q48-72h",
  "hd": "15-20 mg/kg after HD",
  "cvvhdf": "15-20 mg/kg q24h"
}
```

### Special Dosing Categories Found:
1. **Infection-specific doses**: Meningitis, Bacteremia, Pneumonia
2. **Loading doses**: Vancomycin, Piperacillin-tazobactam (extended infusion)
3. **Weight-based**: Vancomycin, Daptomycin, Gentamicin, Tobramycin
4. **Extended infusion**: Cefepime, Piperacillin-tazobactam, Meropenem
5. **BMI-adjusted**: Acyclovir (if BMI ≥35, use AdjBW)

---

## Dosing Calculation Logic

### Step-by-Step Process:

1. **Identify Drug from Selection Step**
   - Input: "Vancomycin + Ceftriaxone for meningitis"
   - Parse: `drugs = ["Vancomycin", "Ceftriaxone"]`, `indication = "meningitis"`

2. **Look up Infection-Specific Dosing Entry**
   ```python
   # Priority order:
   # 1. Infection-specific entry (e.g., "Vancomycin IV (Meningitis)")
   # 2. Loading dose entry if applicable
   # 3. Standard dose entry

   if indication == "meningitis":
       dosing_entry = find_entry("Vancomycin IV (Meningitis)")
   if not dosing_entry:
       dosing_entry = find_entry("Vancomycin IV (Standard dose)")
   ```

3. **Calculate Weight to Use**
   ```python
   if drug.requires_weight_based_dosing:
       if BMI >= 35 and drug == "Acyclovir":
           weight = adjusted_body_weight
       elif total_body_weight < ideal_body_weight:
           weight = total_body_weight
       elif total_body_weight > (1.2 * ideal_body_weight):
           weight = adjusted_body_weight
       else:
           weight = ideal_body_weight
   ```

4. **Determine Renal Function Category**
   ```python
   if on_dialysis:
       if dialysis_type == "HD":
           category = "hd"
       elif dialysis_type == "CVVHDF":
           category = "cvvhdf"
   elif creatinine_clearance > 50:
       category = "crcl_gt_50"
   elif 30 <= creatinine_clearance <= 50:
       category = "crcl_50_30"
   elif 10 <= creatinine_clearance <= 29:
       category = "crcl_29_10"
   else:
       category = "crcl_lt_10_no_hd"
   ```

5. **Apply Loading Dose Logic**
   ```python
   if indication in ["meningitis", "severe_sepsis"] and drug == "Vancomycin":
       loading_dose = dosing_entry["ed_once_dose"]  # 25-30 mg/kg
       maintenance_dose = dosing_entry[renal_category]
       return {
           "loading": loading_dose,
           "maintenance": maintenance_dose
       }
   ```

6. **Check for Special Adjustments**
   - Recent surgery within 48 hours → May need dose adjustment
   - Septic shock → May need higher dose or loading dose
   - Extended infusion protocols → Special administration instructions

7. **Format Final Dosing Recommendation**
   ```json
   {
     "drug": "Vancomycin",
     "loading_dose": {
       "dose": "25-30 mg/kg IV",
       "calculated_dose_range": "1750-2100 mg IV",  // Based on 70kg
       "route": "IV",
       "frequency": "x1",
       "infusion_time": "Over 1-2 hours"
     },
     "maintenance_dose": {
       "dose": "15-20 mg/kg IV",
       "calculated_dose_range": "1050-1400 mg IV",
       "route": "IV",
       "frequency": "q12h",  // Based on CrCl 44
       "infusion_time": "Over 1-2 hours"
     },
     "monitoring": [
       "Trough levels before 4th dose (target 15-20 mcg/mL for meningitis)",
       "Renal function (SCr, BUN)",
       "Consider AUC-guided dosing"
     ],
     "duration": "Duration varies by clinical response and source control",
     "renal_adjustment_rationale": "CrCl 44 mL/min → q12h dosing interval"
   }
   ```

---

## Implementation Plan

### Phase 1: Create Dosing Module (Python)
**File**: `dosing_calculator.py`

```python
class DosingCalculator:
    def __init__(self, dosing_table_json):
        self.dosing_table = dosing_table_json

    def calculate_dose(self,
                      drug_name: str,
                      indication: str,
                      patient_params: dict) -> dict:
        """
        Main dosing calculation function

        Args:
            drug_name: e.g., "Vancomycin", "Ceftriaxone"
            indication: e.g., "meningitis", "bacteremia", "pneumonia"
            patient_params: All patient-specific factors

        Returns:
            Detailed dosing recommendation with rationale
        """
        pass

    def find_dosing_entry(self, drug_name: str, indication: str = None):
        """Find appropriate dosing table entry"""
        pass

    def calculate_weight_to_use(self, patient_params: dict, drug_name: str):
        """Determine IBW vs TBW vs AdjBW"""
        pass

    def determine_renal_category(self, patient_params: dict):
        """Map renal function to dosing category"""
        pass

    def apply_loading_dose_logic(self, drug_name: str, indication: str, severity: str):
        """Determine if loading dose needed"""
        pass
```

### Phase 2: Modify Agent Workflow
1. **Drug Selection Agent** outputs: Drug names + indication
2. **Dosing Calculator** (deterministic) outputs: Exact doses
3. **Final Formatter Agent** combines: Clinical guidance + specific dosing

### Phase 3: Enhanced Patient Input JSON
Create comprehensive input schema (see next section)

---

## Complete Patient Input JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TUHS Antibiotic Steward - Complete Patient Input",
  "type": "object",
  "required": [
    "age",
    "gender",
    "weight",
    "renal_function",
    "infection",
    "allergies"
  ],
  "properties": {
    "patient_id": {
      "type": ["string", "null"],
      "description": "Optional patient identifier (de-identified)"
    },

    "age": {
      "type": "integer",
      "minimum": 0,
      "maximum": 120,
      "description": "Patient age in years"
    },

    "gender": {
      "type": "string",
      "enum": ["male", "female", "other"],
      "description": "Patient gender (affects Cockcroft-Gault calculation)"
    },

    "weight": {
      "type": "object",
      "required": ["total_body_weight_kg"],
      "properties": {
        "total_body_weight_kg": {"type": "number", "minimum": 1},
        "height_cm": {"type": ["number", "null"]},
        "ideal_body_weight_kg": {"type": ["number", "null"]},
        "adjusted_body_weight_kg": {"type": ["number", "null"]},
        "bmi": {"type": ["number", "null"]},
        "weight_to_use": {
          "type": ["string", "null"],
          "enum": ["IBW", "TBW", "AdjBW", null],
          "description": "Override automatic weight selection"
        }
      }
    },

    "renal_function": {
      "type": "object",
      "required": ["creatinine_clearance"],
      "properties": {
        "serum_creatinine": {"type": ["number", "null"]},
        "creatinine_clearance": {
          "type": "number",
          "minimum": 0,
          "description": "CrCl in mL/min (Cockcroft-Gault)"
        },
        "egfr": {
          "type": ["number", "null"],
          "description": "Usually NOT used for dosing"
        },
        "renal_replacement": {
          "type": "object",
          "properties": {
            "on_dialysis": {"type": "boolean"},
            "dialysis_type": {
              "type": ["string", "null"],
              "enum": ["HD", "PD", "CVVHDF", null]
            },
            "last_dialysis": {
              "type": ["string", "null"],
              "format": "date-time"
            },
            "dialysis_schedule": {
              "type": ["string", "null"],
              "description": "e.g., MWF, TThSa, daily"
            }
          }
        }
      }
    },

    "infection": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "pneumonia",
            "cap",
            "hap",
            "vap",
            "cystitis",
            "pyelonephritis",
            "uti",
            "bacteremia",
            "sepsis",
            "meningitis",
            "ssti",
            "cellulitis",
            "abscess",
            "intra_abdominal",
            "neutropenic_fever",
            "central_line_infection"
          ]
        },
        "severity": {
          "type": "string",
          "enum": ["mild", "moderate", "severe", "critical"],
          "default": "moderate"
        },
        "source": {
          "type": ["string", "null"],
          "description": "For sepsis: abdomen, lung, urinary, skin, unknown"
        },
        "onset": {
          "type": "string",
          "enum": ["community", "hospital_acquired", "healthcare_associated"],
          "default": "community"
        },
        "days_hospitalized": {
          "type": "integer",
          "minimum": 0,
          "description": "Used to determine if >48 hours"
        }
      }
    },

    "allergies": {
      "type": "object",
      "properties": {
        "penicillin": {
          "type": "object",
          "properties": {
            "has_allergy": {"type": "boolean"},
            "severity": {
              "type": ["string", "null"],
              "enum": ["mild", "moderate", "severe", null]
            },
            "reaction_type": {
              "type": ["string", "null"],
              "enum": ["rash", "hives", "itching", "anaphylaxis", "sjs", "dress", "angioedema", null]
            }
          }
        },
        "cephalosporin": {"$ref": "#/properties/allergies/properties/penicillin"},
        "sulfa": {"$ref": "#/properties/allergies/properties/penicillin"},
        "fluoroquinolone": {"$ref": "#/properties/allergies/properties/penicillin"},
        "other": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },

    "location": {
      "type": "string",
      "enum": ["Ward", "ICU", "ED"],
      "description": "Patient location"
    },

    "clinical_status": {
      "type": "object",
      "properties": {
        "septic_shock": {"type": "boolean", "default": false},
        "immunocompromised": {"type": "boolean", "default": false},
        "pregnant": {"type": "boolean", "default": false},
        "breastfeeding": {"type": "boolean", "default": false},
        "neutropenic": {"type": "boolean", "default": false},
        "anc": {"type": ["number", "null"], "description": "Absolute neutrophil count"}
      }
    },

    "microbiology": {
      "type": "object",
      "properties": {
        "culture_results": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string",
              "enum": ["pending", "positive", "negative", "contaminated"],
              "default": "pending"
            },
            "organism": {"type": ["string", "null"]},
            "sensitivities": {"type": "object"},
            "mic_values": {"type": "object"}
          }
        },
        "prior_cultures_6mo": {
          "type": "object",
          "properties": {
            "has_mdro": {"type": "boolean", "default": false},
            "organisms": {"type": "array", "items": {"type": "string"}},
            "last_culture_date": {"type": ["string", "null"], "format": "date"}
          }
        },
        "colonization": {
          "type": "object",
          "properties": {
            "mrsa_nares": {"type": ["boolean", "null"]},
            "vre_rectal": {"type": ["boolean", "null"]}
          }
        }
      }
    },

    "current_medications": {
      "type": "object",
      "properties": {
        "antibiotics": {
          "type": "object",
          "properties": {
            "outpatient": {"type": "array", "items": {"type": "string"}},
            "inpatient": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "drug": {"type": "string"},
                  "dose": {"type": "string"},
                  "frequency": {"type": "string"},
                  "route": {"type": "string"},
                  "start_date": {"type": "string", "format": "date"},
                  "days_on_therapy": {"type": "integer"}
                }
              }
            }
          }
        }
      }
    },

    "recent_surgery": {
      "type": "object",
      "properties": {
        "had_surgery": {"type": "boolean", "default": false},
        "surgery_date": {"type": ["string", "null"], "format": "date-time"},
        "surgery_type": {"type": ["string", "null"]},
        "on_tpn": {"type": "boolean", "default": false}
      }
    }
  }
}
```

---

## Example Complete Patient Input

```json
{
  "patient_id": "PT-2025-001",
  "age": 88,
  "gender": "male",

  "weight": {
    "total_body_weight_kg": 70,
    "height_cm": 175,
    "ideal_body_weight_kg": 68,
    "adjusted_body_weight_kg": null,
    "bmi": 22.9,
    "weight_to_use": null
  },

  "renal_function": {
    "serum_creatinine": 1.5,
    "creatinine_clearance": 44,
    "egfr": 45,
    "renal_replacement": {
      "on_dialysis": false,
      "dialysis_type": null,
      "last_dialysis": null,
      "dialysis_schedule": null
    }
  },

  "infection": {
    "type": "bacteremia",
    "severity": "severe",
    "source": "unknown",
    "onset": "hospital_acquired",
    "days_hospitalized": 3
  },

  "allergies": {
    "penicillin": {
      "has_allergy": true,
      "severity": "severe",
      "reaction_type": "anaphylaxis"
    },
    "cephalosporin": {
      "has_allergy": false,
      "severity": null,
      "reaction_type": null
    },
    "sulfa": {
      "has_allergy": false,
      "severity": null,
      "reaction_type": null
    },
    "fluoroquinolone": {
      "has_allergy": false,
      "severity": null,
      "reaction_type": null
    },
    "other": []
  },

  "location": "Ward",

  "clinical_status": {
    "septic_shock": false,
    "immunocompromised": false,
    "pregnant": false,
    "breastfeeding": false,
    "neutropenic": false,
    "anc": null
  },

  "microbiology": {
    "culture_results": {
      "status": "pending",
      "organism": null,
      "sensitivities": {},
      "mic_values": {}
    },
    "prior_cultures_6mo": {
      "has_mdro": true,
      "organisms": ["MRSA"],
      "last_culture_date": "2025-09-15"
    },
    "colonization": {
      "mrsa_nares": true,
      "vre_rectal": null
    }
  },

  "current_medications": {
    "antibiotics": {
      "outpatient": [],
      "inpatient": []
    }
  },

  "recent_surgery": {
    "had_surgery": true,
    "surgery_date": "2025-10-02T10:30:00Z",
    "surgery_type": "abdominal",
    "on_tpn": true
  }
}
```

---

## Next Steps

1. ✅ Create this architecture document
2. ⏳ Implement `dosing_calculator.py` module
3. ⏳ Update `agno_bridge_v2.py` to return drug selections without doses
4. ⏳ Integrate dosing calculator into FastAPI workflow
5. ⏳ Update frontend to collect comprehensive patient data
6. ⏳ Add dosing validation and safety checks
7. ⏳ Create comprehensive test cases for all dosing scenarios

