"""
Recommendation Engine - Integrates all v3 components

This module provides a unified interface for antibiotic recommendations:
- Step 1: DrugSelector selects appropriate drugs
- Step 2: DoseCalculator calculates precise dosing
- Step 3: Format and return complete recommendation

Usage:
    engine = RecommendationEngine()
    result = engine.get_recommendation({
        'age': 55,
        'infection_type': 'uti',
        'fever': True,
        'allergies': 'Penicillin (rash)',
        'weight': 70,
        'crcl': 60
    })
"""

import logging
from typing import Dict, Any
from lib.guideline_loader_v3 import GuidelineLoaderV3
from lib.drug_selector import DrugSelector
from lib.dose_calculator import DoseCalculator

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Unified recommendation engine using v3 architecture"""

    def __init__(self):
        """Initialize engine with loader, selector, and calculator"""
        logger.info("Initializing RecommendationEngine v3")
        
        # Load guidelines
        self.loader = GuidelineLoaderV3()
        success = self.loader.load_all()
        
        if not success:
            raise RuntimeError("Failed to load guidelines")
        
        # Initialize components
        self.selector = DrugSelector(self.loader)
        self.calculator = DoseCalculator(self.loader)
        
        logger.info("RecommendationEngine v3 initialized successfully")

    def get_recommendation(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete antibiotic recommendation

        Args:
            patient_data: Dictionary with:
                - age: Patient age (int)
                - infection_type: 'uti', 'pneumonia', 'intra_abdominal', etc.
                - allergies: Free-text allergy description (optional)
                - pregnancy: Boolean or trimester (optional)
                - fever: Boolean (optional)
                - severity: 'mild', 'moderate', 'severe' (optional)
                - weight: Weight in kg (optional, for vancomycin)
                - crcl: Creatinine clearance (optional, for renal adjustment)

        Returns:
            Dictionary with:
                - success: Boolean
                - recommendation: Formatted text recommendation
                - drugs: List of drug dosing details
                - infection_category: Determined infection category
                - allergy_classification: Allergy classification
                - warnings: List of warnings
                - errors: List of errors (if any)
                - metadata: Additional context
        """
        logger.info(f"Processing recommendation for: {patient_data.get('infection_type')}")

        try:
            # Step 1: Select appropriate drugs
            selection_result = self.selector.select_drugs(patient_data)

            if selection_result['errors']:
                logger.error(f"Drug selection errors: {selection_result['errors']}")
                return {
                    'success': False,
                    'errors': selection_result['errors'],
                    'infection_category': selection_result.get('infection_category'),
                    'allergy_classification': selection_result.get('allergy_classification')
                }

            drug_ids = selection_result['drug_ids']
            
            if not drug_ids:
                return {
                    'success': False,
                    'errors': ['No appropriate drugs found for this patient'],
                    'infection_category': selection_result.get('infection_category'),
                    'allergy_classification': selection_result.get('allergy_classification')
                }

            # Step 2: Calculate precise dosing
            dosing_result = self.calculator.calculate_regimen(
                drug_ids=drug_ids,
                indication=selection_result['infection_category'],
                crcl=patient_data.get('crcl'),
                weight=patient_data.get('weight'),
                patient_age=patient_data.get('age')
            )

            if dosing_result['errors']:
                logger.error(f"Dosing calculation errors: {dosing_result['errors']}")
                return {
                    'success': False,
                    'errors': dosing_result['errors'],
                    'drug_ids': drug_ids,
                    'infection_category': selection_result['infection_category']
                }

            # Step 3: Format complete recommendation
            recommendation_text = self._format_recommendation(
                selection_result=selection_result,
                dosing_result=dosing_result,
                patient_data=patient_data
            )

            # Combine warnings from both steps
            all_warnings = list(set(selection_result['warnings'] + dosing_result['warnings']))

            return {
                'success': True,
                'recommendation': recommendation_text,
                'drugs': dosing_result['drugs'],
                'infection_category': selection_result['infection_category'],
                'allergy_classification': selection_result['allergy_classification'],
                'route': selection_result['route'],
                'warnings': all_warnings,
                'monitoring': dosing_result['monitoring'],
                'rationale': selection_result['rationale'],
                'errors': [],
                'metadata': {
                    'version': '3.0.0',
                    'architecture': 'modular_v3',
                    'drug_count': len(dosing_result['drugs'])
                }
            }

        except Exception as e:
            logger.error(f"Error in recommendation engine: {e}", exc_info=True)
            return {
                'success': False,
                'errors': [f"Internal error: {str(e)}"],
                'recommendation': None
            }

    def _format_recommendation(
        self,
        selection_result: Dict[str, Any],
        dosing_result: Dict[str, Any],
        patient_data: Dict[str, Any]
    ) -> str:
        """Format recommendation as human-readable text"""
        lines = []

        # Header
        lines.append("="*70)
        lines.append("ANTIBIOTIC RECOMMENDATION")
        lines.append("="*70)
        lines.append("")

        # Patient context
        lines.append("**PATIENT CONTEXT:**")
        lines.append(f"  Age: {patient_data.get('age', 'Unknown')}")
        lines.append(f"  Infection: {selection_result['infection_category']}")
        lines.append(f"  Allergy Status: {selection_result['allergy_classification']}")
        if patient_data.get('crcl'):
            lines.append(f"  Renal Function: CrCl {patient_data['crcl']} mL/min")
        if patient_data.get('weight'):
            lines.append(f"  Weight: {patient_data['weight']} kg")
        lines.append("")

        # Recommended regimen
        lines.append("**RECOMMENDED REGIMEN:**")
        lines.append("")

        for idx, drug in enumerate(dosing_result['drugs'], 1):
            lines.append(f"{idx}. **{drug['drug_name']}** ({drug['class']})")
            
            # Loading dose
            if drug.get('loading_dose'):
                if drug.get('calculated_dose', {}).get('loading_dose_calculated'):
                    lines.append(f"   Loading Dose: {drug['calculated_dose']['loading_dose_calculated']}")
                else:
                    lines.append(f"   Loading Dose: {drug['loading_dose']}")

            # Maintenance dose
            if drug.get('calculated_dose', {}).get('maintenance_dose_calculated'):
                lines.append(f"   Maintenance: {drug['calculated_dose']['maintenance_dose_calculated']}")
            else:
                dose_str = f"{drug['dose']} {drug['frequency']}"
                lines.append(f"   Dose: {dose_str}")

            lines.append(f"   Route: {drug['route']}")
            
            if drug.get('duration'):
                lines.append(f"   Duration: {drug['duration']}")

            # Coverage
            if drug.get('coverage'):
                coverage = ', '.join(drug['coverage'])
                lines.append(f"   Coverage: {coverage}")

            # Renal adjustment note
            if drug.get('renal_adjusted'):
                lines.append(f"   ⚠️ DOSE ADJUSTED for CrCl {patient_data.get('crcl')} mL/min")

            lines.append("")

        # Rationale
        if selection_result.get('rationale'):
            lines.append("**RATIONALE:**")
            for rationale in selection_result['rationale']:
                lines.append(f"  • {rationale}")
            lines.append("")

        # Monitoring
        if dosing_result.get('monitoring'):
            lines.append("**MONITORING REQUIRED:**")
            for monitor in set(dosing_result['monitoring']):
                lines.append(f"  • {monitor}")
            lines.append("")

        # Warnings
        all_warnings = list(set(selection_result['warnings'] + dosing_result['warnings']))
        if all_warnings:
            lines.append("**⚠️ WARNINGS:**")
            for warning in all_warnings:
                lines.append(f"  • {warning}")
            lines.append("")

        # Footer
        lines.append("="*70)
        lines.append("🤖 Generated with TUHS Antibiotic Steward v3.0")
        lines.append("="*70)

        return '\n'.join(lines)


# Convenience function for testing
def main():
    """Test recommendation engine"""
    logging.basicConfig(level=logging.INFO)

    engine = RecommendationEngine()

    # Test Case 1: Pyelonephritis with mild PCN allergy
    print("\n" + "="*70)
    print("Test Case 1: Pyelonephritis + Mild PCN Allergy")
    print("="*70)
    result = engine.get_recommendation({
        'age': 55,
        'infection_type': 'uti',
        'fever': True,
        'allergies': 'Penicillin (rash)',
        'weight': 70,
        'crcl': 60
    })
    
    if result['success']:
        print(result['recommendation'])
    else:
        print(f"❌ Error: {result['errors']}")

    # Test Case 2: Intra-abdominal with severe PCN allergy
    print("\n" + "="*70)
    print("Test Case 2: Intra-abdominal + Severe PCN Allergy")
    print("="*70)
    result = engine.get_recommendation({
        'age': 65,
        'infection_type': 'intra_abdominal',
        'allergies': 'Penicillin - anaphylaxis',
        'severity': 'moderate',
        'weight': 80,
        'crcl': 45
    })
    
    if result['success']:
        print(result['recommendation'])
    else:
        print(f"❌ Error: {result['errors']}")

    # Test Case 3: Meningitis with vancomycin loading dose
    print("\n" + "="*70)
    print("Test Case 3: Meningitis (loading dose required)")
    print("="*70)
    result = engine.get_recommendation({
        'age': 42,
        'infection_type': 'meningitis',
        'weight': 70,
        'crcl': 90
    })
    
    if result['success']:
        print(result['recommendation'])
    else:
        print(f"❌ Error: {result['errors']}")


if __name__ == '__main__':
    main()
