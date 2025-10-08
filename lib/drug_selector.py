"""
DrugSelector - Step 1 of antibiotic recommendation pipeline

This class selects appropriate antibiotics based on:
- Infection type and severity
- Allergy status (mild vs severe PCN allergy)
- Pregnancy status
- Route requirement (IV vs PO)

Architecture:
    Step 1 (DrugSelector): Patient data → List of appropriate drug IDs
    Step 2 (DoseCalculator): Drug IDs + patient factors → Precise dosing
    Step 3 (Validator): Dosing recommendations → Final validation

Usage:
    selector = DrugSelector(loader)
    result = selector.select_drugs({
        'age': 55,
        'infection_type': 'uti',
        'fever': True,
        'allergies': 'Penicillin (rash)',
        'pregnancy': None,
        'crcl': 60
    })
"""

import logging
from typing import Dict, List, Any, Optional
from lib.guideline_loader_v3 import GuidelineLoaderV3

logger = logging.getLogger(__name__)


class DrugSelector:
    """Select appropriate antibiotics based on patient factors"""

    def __init__(self, loader: GuidelineLoaderV3):
        """
        Initialize drug selector

        Args:
            loader: GuidelineLoaderV3 instance with loaded guidelines
        """
        self.loader = loader

    def select_drugs(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select appropriate antibiotics for patient

        Args:
            patient_data: Dictionary with keys:
                - infection_type: 'uti', 'pneumonia', 'intra_abdominal', etc.
                - age: Patient age
                - allergies: Free-text allergy description (optional)
                - pregnancy: Boolean or trimester number (optional)
                - fever: Boolean (optional)
                - severity: 'mild', 'moderate', 'severe' (optional)
                - location: 'community', 'hospital', 'icu' (optional)

        Returns:
            Dictionary with:
                - drug_ids: List of drug IDs
                - infection_category: Specific infection subcategory
                - allergy_classification: 'no_allergy', 'mild_pcn', 'severe_pcn'
                - route: 'IV' or 'PO'
                - rationale: Explanation of drug selection
                - warnings: List of critical warnings
                - errors: List of errors (if any)
        """
        result = {
            'drug_ids': [],
            'infection_category': None,
            'allergy_classification': 'no_allergy',
            'route': None,
            'rationale': [],
            'warnings': [],
            'errors': []
        }

        try:
            # Step 1: Determine infection category
            infection_category, route = self._determine_infection_category(patient_data)
            result['infection_category'] = infection_category
            result['route'] = route

            if not infection_category:
                result['errors'].append('Could not determine infection category')
                return result

            # Step 2: Classify allergy severity
            allergy_status = self._classify_allergy(patient_data.get('allergies'))
            result['allergy_classification'] = allergy_status

            # Step 3: Check pregnancy contraindications
            pregnancy_blocked_drugs = []
            if patient_data.get('pregnancy'):
                pregnancy_blocked_drugs = self._get_pregnancy_blocked_drugs(patient_data)

            # Step 4: Get regimens from infection guidelines
            infection_type = patient_data.get('infection_type')
            regimens = self.loader.get_infection_regimens(
                infection_type=infection_type,
                subcategory=infection_category,
                allergy_status=allergy_status
            )

            if not regimens:
                # Try without subcategory
                regimens = self.loader.get_infection_regimens(
                    infection_type=infection_type,
                    allergy_status=allergy_status
                )

            if not regimens:
                result['errors'].append(f'No regimens found for {infection_type} + {allergy_status}')
                return result

            # Step 5: Select best regimen and filter drugs
            selected_drugs = []
            for regimen in regimens:
                drugs = regimen.get('drugs', [])

                # Filter out pregnancy-contraindicated drugs
                if pregnancy_blocked_drugs:
                    drugs = [d for d in drugs if d not in pregnancy_blocked_drugs]

                if drugs:
                    selected_drugs = drugs
                    result['rationale'].append(regimen.get('reasoning', 'Standard regimen'))

                    # Add warnings from regimen
                    if regimen.get('note'):
                        result['warnings'].append(regimen['note'])

                    break  # Use first matching regimen

            result['drug_ids'] = selected_drugs

            # Step 6: Add critical warnings
            critical_rules = self.loader.get_critical_rules(infection_type)
            result['warnings'].extend(critical_rules)

            # Step 7: Validate route requirement
            if route and route == 'IV':
                iv_warning = f"⚠️ {infection_category} requires IV antibiotics"
                if iv_warning not in result['warnings']:
                    result['warnings'].append(iv_warning)

        except Exception as e:
            logger.error(f"Error in drug selection: {e}", exc_info=True)
            result['errors'].append(f"Selection error: {str(e)}")

        return result

    def _determine_infection_category(
        self,
        patient_data: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Determine specific infection category from patient data

        Returns:
            Tuple of (infection_category, route_requirement)
        """
        infection_type = patient_data.get('infection_type')

        # UTI - Check for fever to distinguish pyelonephritis
        if infection_type == 'uti':
            if patient_data.get('fever'):
                return 'pyelonephritis', 'IV'
            else:
                # Check for pyelonephritis keywords
                presentation = str(patient_data.get('presentation', '')).lower()
                if any(keyword in presentation for keyword in ['flank', 'costovertebral', 'cvat']):
                    return 'pyelonephritis', 'IV'
                return 'cystitis', 'PO'

        # Pneumonia - Determine type
        elif infection_type == 'pneumonia':
            location = patient_data.get('location', 'community').lower()
            if 'icu' in location or patient_data.get('severity') == 'severe':
                return 'severe_cap', 'IV'
            elif 'hospital' in location or 'hap' in location:
                return 'hap', 'IV'
            elif 'ventilator' in location or 'vap' in location:
                return 'vap', 'IV'
            elif 'aspiration' in str(patient_data.get('presentation', '')).lower():
                return 'aspiration', 'IV'
            else:
                return 'cap', 'IV'  # Default to CAP

        # Intra-abdominal
        elif infection_type == 'intra_abdominal':
            severity = patient_data.get('severity', 'moderate')
            if severity == 'severe':
                return 'severe_intra_abdominal', 'IV'
            else:
                return 'moderate_intra_abdominal', 'IV'

        # Bacteremia/Sepsis
        elif infection_type == 'bacteremia' or infection_type == 'sepsis':
            if patient_data.get('mrsa_risk') or 'mrsa' in str(patient_data.get('presentation', '')).lower():
                return 'bacteremia_mrsa', 'IV'
            else:
                return 'bacteremia', 'IV'

        # Meningitis
        elif infection_type == 'meningitis':
            return 'bacterial_meningitis', 'IV'

        # Default - return infection type as-is
        return infection_type, 'IV'

    def _classify_allergy(self, allergy_description: Optional[str]) -> str:
        """
        Classify allergy severity

        Returns:
            'no_allergy', 'mild_pcn', 'severe_pcn', or 'other'
        """
        if not allergy_description:
            return 'no_allergy'

        # Check if PCN allergy
        allergy_lower = allergy_description.lower()
        if not any(term in allergy_lower for term in ['penicillin', 'pcn', 'pen ']):
            return 'other'  # Non-PCN allergy

        # Classify severity using loader
        severity = self.loader.classify_allergy_severity(allergy_description)

        if severity == 'severe':
            return 'severe_pcn_allergy'
        elif severity == 'mild':
            return 'mild_pcn_allergy'
        else:
            # Default to mild if unclear
            return 'mild_pcn_allergy'

    def _get_pregnancy_blocked_drugs(self, patient_data: Dict[str, Any]) -> List[str]:
        """
        Get list of drugs contraindicated in pregnancy

        Returns:
            List of drug IDs to block
        """
        blocked_drugs = []

        pregnancy = patient_data.get('pregnancy')
        trimester = None

        # Determine trimester
        if isinstance(pregnancy, int):
            trimester = pregnancy
        elif isinstance(pregnancy, str):
            if 'first' in pregnancy.lower() or '1' in pregnancy:
                trimester = 1
            elif 'second' in pregnancy.lower() or '2' in pregnancy:
                trimester = 2
            elif 'third' in pregnancy.lower() or '3' in pregnancy:
                trimester = 3

        # Check all drugs for pregnancy safety
        all_drug_ids = self.loader.get_all_drug_ids()
        for drug_id in all_drug_ids:
            safe, reason = self.loader.check_pregnancy_safe(drug_id, trimester)
            if not safe:
                blocked_drugs.append(drug_id)
                logger.info(f"Blocking {drug_id} in pregnancy: {reason}")

        return blocked_drugs


# Convenience function for testing
def main():
    """Test drug selector functionality"""
    logging.basicConfig(level=logging.INFO)

    # Load guidelines
    loader = GuidelineLoaderV3()
    if not loader.load_all():
        print("❌ Failed to load guidelines")
        return

    selector = DrugSelector(loader)

    # Test Case 1: Pyelonephritis with mild PCN allergy
    print("\n" + "="*60)
    print("Test Case 1: Pyelonephritis with mild PCN allergy")
    print("="*60)
    result = selector.select_drugs({
        'age': 55,
        'infection_type': 'uti',
        'fever': True,
        'allergies': 'Penicillin (rash)'
    })
    print(f"Infection: {result['infection_category']}")
    print(f"Allergy: {result['allergy_classification']}")
    print(f"Route: {result['route']}")
    print(f"Drugs: {result['drug_ids']}")
    print(f"Rationale: {result['rationale']}")
    print(f"Warnings: {result['warnings']}")

    # Test Case 2: Intra-abdominal with severe PCN allergy
    print("\n" + "="*60)
    print("Test Case 2: Intra-abdominal with severe PCN allergy")
    print("="*60)
    result = selector.select_drugs({
        'age': 65,
        'infection_type': 'intra_abdominal',
        'allergies': 'Penicillin - anaphylaxis',
        'severity': 'moderate'
    })
    print(f"Infection: {result['infection_category']}")
    print(f"Allergy: {result['allergy_classification']}")
    print(f"Route: {result['route']}")
    print(f"Drugs: {result['drug_ids']}")
    print(f"Rationale: {result['rationale']}")

    # Test Case 3: CAP with pregnancy
    print("\n" + "="*60)
    print("Test Case 3: Pneumonia in pregnancy")
    print("="*60)
    result = selector.select_drugs({
        'age': 28,
        'infection_type': 'pneumonia',
        'pregnancy': '2nd trimester',
        'location': 'community'
    })
    print(f"Infection: {result['infection_category']}")
    print(f"Allergy: {result['allergy_classification']}")
    print(f"Route: {result['route']}")
    print(f"Drugs: {result['drug_ids']}")
    print(f"Rationale: {result['rationale']}")

    # Test Case 4: Bacteremia MRSA
    print("\n" + "="*60)
    print("Test Case 4: Bacteremia with MRSA risk")
    print("="*60)
    result = selector.select_drugs({
        'age': 72,
        'infection_type': 'bacteremia',
        'mrsa_risk': True
    })
    print(f"Infection: {result['infection_category']}")
    print(f"Allergy: {result['allergy_classification']}")
    print(f"Route: {result['route']}")
    print(f"Drugs: {result['drug_ids']}")
    print(f"Rationale: {result['rationale']}")

    # Test Case 5: Cystitis (no fever)
    print("\n" + "="*60)
    print("Test Case 5: Simple cystitis (no fever)")
    print("="*60)
    result = selector.select_drugs({
        'age': 42,
        'infection_type': 'uti',
        'fever': False
    })
    print(f"Infection: {result['infection_category']}")
    print(f"Allergy: {result['allergy_classification']}")
    print(f"Route: {result['route']}")
    print(f"Drugs: {result['drug_ids']}")
    print(f"Rationale: {result['rationale']}")


if __name__ == '__main__':
    main()
