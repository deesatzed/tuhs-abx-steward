"""
DoseCalculator - Step 2 of antibiotic recommendation pipeline

This class calculates precise dosing for selected antibiotics based on:
- Indication (different doses for same drug depending on infection type)
- Renal function (CrCl-based adjustments)
- Loading doses (for severe infections like meningitis, bacteremia)
- Monitoring requirements (vancomycin troughs, etc.)

Architecture:
    Step 1 (DrugSelector): Patient data → List of appropriate drug IDs
    Step 2 (DoseCalculator): Drug IDs + patient factors → Precise dosing
    Step 3 (Validator): Dosing recommendations → Final validation

Usage:
    calculator = DoseCalculator(loader)
    result = calculator.calculate_regimen(
        drug_ids=['ceftriaxone', 'vancomycin'],
        indication='meningitis',
        crcl=45,
        weight=70
    )
"""

import logging
from typing import Dict, List, Any, Optional
from lib.guideline_loader_v3 import GuidelineLoaderV3

logger = logging.getLogger(__name__)


class DoseCalculator:
    """Calculate precise antibiotic dosing based on indication and patient factors"""

    def __init__(self, loader: GuidelineLoaderV3):
        """
        Initialize dose calculator

        Args:
            loader: GuidelineLoaderV3 instance with loaded guidelines
        """
        self.loader = loader

    def calculate_regimen(
        self,
        drug_ids: List[str],
        indication: str,
        crcl: Optional[float] = None,
        weight: Optional[float] = None,
        patient_age: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate complete dosing regimen for selected drugs

        Args:
            drug_ids: List of drug IDs from DrugSelector
            indication: Specific indication (e.g., 'pyelonephritis', 'meningitis')
            crcl: Creatinine clearance in mL/min (optional)
            weight: Patient weight in kg (for weight-based dosing like vancomycin)
            patient_age: Patient age (for elderly warnings)

        Returns:
            Dictionary with:
                - drugs: List of drug dosing dictionaries
                - monitoring: List of monitoring requirements
                - warnings: List of warnings
                - errors: List of errors (if any)
        """
        result = {
            'drugs': [],
            'monitoring': [],
            'warnings': [],
            'errors': []
        }

        try:
            for drug_id in drug_ids:
                drug_dose = self._calculate_drug_dose(
                    drug_id=drug_id,
                    indication=indication,
                    crcl=crcl,
                    weight=weight,
                    patient_age=patient_age
                )

                if drug_dose:
                    result['drugs'].append(drug_dose)

                    # Add monitoring requirements
                    if drug_dose.get('monitoring'):
                        result['monitoring'].extend(drug_dose['monitoring'])

                    # Add warnings
                    if drug_dose.get('warnings'):
                        result['warnings'].extend(drug_dose['warnings'])
                else:
                    result['errors'].append(f"Could not calculate dose for {drug_id}")

            # Add general warnings
            if crcl and crcl < 30:
                result['warnings'].append("⚠️ Severe renal impairment - consult pharmacist for complex dosing")

            if patient_age and patient_age >= 65:
                result['warnings'].append("⚠️ Elderly patient - monitor for adverse effects")

        except Exception as e:
            logger.error(f"Error calculating regimen: {e}", exc_info=True)
            result['errors'].append(f"Calculation error: {str(e)}")

        return result

    def _calculate_drug_dose(
        self,
        drug_id: str,
        indication: str,
        crcl: Optional[float],
        weight: Optional[float],
        patient_age: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate dose for a single drug

        Returns:
            Dictionary with dose, frequency, route, duration, monitoring, warnings
        """
        # Normalize indication (remove severity/type prefixes and suffixes)
        # e.g., "moderate_intra_abdominal" -> "intra_abdominal"
        # e.g., "bacterial_meningitis" -> "meningitis"
        # e.g., "bacteremia_mrsa" -> "bacteremia"
        normalized_indication = indication

        # Remove prefixes
        for prefix in ['mild_', 'moderate_', 'severe_', 'community_', 'hospital_', 'bacterial_']:
            if indication.startswith(prefix):
                normalized_indication = indication.replace(prefix, '', 1)
                break

        # Remove suffixes
        for suffix in ['_mrsa', '_sepsis', '_source']:
            if normalized_indication.endswith(suffix):
                normalized_indication = normalized_indication.replace(suffix, '', 1)
                break

        # Get base dose from loader
        dose_info = self.loader.get_drug_dose(drug_id, normalized_indication, crcl)

        if not dose_info:
            logger.warning(f"No dosing info found for {drug_id} + {indication}")
            return None

        # Enrich with additional information
        drug_data = self.loader.drugs.get(drug_id, {})

        # Build comprehensive dose dictionary
        # Handle both "dose" and "maintenance_dose" fields
        dose_value = dose_info.get('dose') or dose_info.get('maintenance_dose')

        result = {
            'drug_id': drug_id,
            'drug_name': dose_info.get('drug_name', drug_id),
            'dose': dose_value,
            'frequency': dose_info.get('frequency'),
            'route': dose_info.get('route'),
            'duration': dose_info.get('duration'),
            'monitoring': [],
            'warnings': [],
            'notes': []
        }

        # Add loading dose if applicable
        if dose_info.get('loading_dose'):
            result['loading_dose'] = dose_info['loading_dose']
            result['notes'].append(f"Loading dose: {dose_info['loading_dose']}")

        # Add indication-specific notes
        if dose_info.get('note'):
            result['notes'].append(dose_info['note'])

        if dose_info.get('critical_note'):
            result['warnings'].append(dose_info['critical_note'])

        # Add renal adjustment information
        if dose_info.get('renal_adjusted'):
            result['renal_adjusted'] = True
            result['original_dose'] = dose_info.get('original_dose')
            if dose_info.get('renal_note'):
                result['notes'].append(dose_info['renal_note'])
            result['warnings'].append(f"⚠️ Dose adjusted for CrCl {crcl} mL/min")

        # Add monitoring requirements from drug data
        monitoring_data = drug_data.get('monitoring', {})
        if isinstance(monitoring_data, dict):
            required_monitoring = monitoring_data.get('required', [])
            result['monitoring'].extend(required_monitoring)

        # Add weight-based dosing calculation for vancomycin
        if drug_id == 'vancomycin' and weight:
            result['calculated_dose'] = self._calculate_vancomycin_dose(dose_info, weight)
            result['notes'].append(f"Calculated for {weight} kg patient")

        # Add nephrotoxic warning
        if drug_data.get('renal_adjustment', {}).get('critical'):
            result['warnings'].append(f"⚠️ {drug_id.capitalize()} is nephrotoxic - monitor renal function")

        # Add drug class information
        result['class'] = drug_data.get('class', 'Unknown')

        # Add spectrum information for rationale
        spectrum = drug_data.get('spectrum', {})
        if spectrum:
            coverage = []
            if spectrum.get('gram_positive') and 'Excellent' in str(spectrum['gram_positive']):
                coverage.append('gram-positive')
            if spectrum.get('gram_negative') and 'Excellent' in str(spectrum['gram_negative']):
                coverage.append('gram-negative')
            if spectrum.get('anaerobes') and 'Excellent' in str(spectrum['anaerobes']):
                coverage.append('anaerobes')
            if coverage:
                result['coverage'] = coverage

        return result

    def _calculate_vancomycin_dose(
        self,
        dose_info: Dict[str, Any],
        weight: float
    ) -> Dict[str, Any]:
        """
        Calculate weight-based vancomycin dose

        Args:
            dose_info: Base dose information
            weight: Patient weight in kg

        Returns:
            Dictionary with calculated loading and maintenance doses
        """
        # Extract mg/kg from dose strings
        # e.g., "15-20 mg/kg IV" -> use midpoint 17.5 mg/kg
        loading_dose_str = dose_info.get('loading_dose', '')
        maintenance_dose_str = dose_info.get('maintenance_dose', dose_info.get('dose', ''))

        result = {}

        # Calculate loading dose (if indicated)
        if 'loading_dose' in dose_info and '25-30 mg/kg' in loading_dose_str:
            loading_mg_kg = 27.5  # Midpoint
            loading_dose_mg = int(loading_mg_kg * weight)
            # Round to nearest 250 mg
            loading_dose_mg = round(loading_dose_mg / 250) * 250
            result['loading_dose_calculated'] = f"{loading_dose_mg} mg IV once"

        # Calculate maintenance dose
        if '15-20 mg/kg' in maintenance_dose_str:
            maintenance_mg_kg = 17.5  # Midpoint
            maintenance_dose_mg = int(maintenance_mg_kg * weight)
            # Round to nearest 250 mg
            maintenance_dose_mg = round(maintenance_dose_mg / 250) * 250
            frequency = dose_info.get('frequency', 'q8-12h')
            result['maintenance_dose_calculated'] = f"{maintenance_dose_mg} mg IV {frequency}"

        return result

    def format_recommendation(self, regimen: Dict[str, Any]) -> str:
        """
        Format dosing recommendation as human-readable text

        Args:
            regimen: Output from calculate_regimen()

        Returns:
            Formatted recommendation string
        """
        lines = []

        # Header
        lines.append("="*60)
        lines.append("ANTIBIOTIC DOSING RECOMMENDATION")
        lines.append("="*60)
        lines.append("")

        # Drugs
        for idx, drug in enumerate(regimen['drugs'], 1):
            lines.append(f"{idx}. **{drug['drug_name']}** ({drug['class']})")

            # Loading dose
            if drug.get('loading_dose'):
                lines.append(f"   Loading Dose: {drug['loading_dose']}")

            # Maintenance dose
            dose_str = f"{drug['dose']} {drug['frequency']}"
            if drug.get('calculated_dose'):
                calc = drug['calculated_dose']
                if calc.get('loading_dose_calculated'):
                    lines.append(f"   Loading: {calc['loading_dose_calculated']}")
                if calc.get('maintenance_dose_calculated'):
                    lines.append(f"   Maintenance: {calc['maintenance_dose_calculated']}")
            else:
                lines.append(f"   Dose: {dose_str}")

            lines.append(f"   Route: {drug['route']}")

            if drug.get('duration'):
                lines.append(f"   Duration: {drug['duration']}")

            # Coverage
            if drug.get('coverage'):
                coverage = ', '.join(drug['coverage'])
                lines.append(f"   Coverage: {coverage}")

            # Notes
            if drug.get('notes'):
                for note in drug['notes']:
                    lines.append(f"   Note: {note}")

            lines.append("")

        # Monitoring
        if regimen['monitoring']:
            lines.append("**Monitoring Required:**")
            for monitor in regimen['monitoring']:
                lines.append(f"  - {monitor}")
            lines.append("")

        # Warnings
        if regimen['warnings']:
            lines.append("**⚠️ WARNINGS:**")
            for warning in regimen['warnings']:
                lines.append(f"  - {warning}")
            lines.append("")

        # Errors
        if regimen['errors']:
            lines.append("**❌ ERRORS:**")
            for error in regimen['errors']:
                lines.append(f"  - {error}")
            lines.append("")

        return '\n'.join(lines)


# Convenience function for testing
def main():
    """Test dose calculator functionality"""
    logging.basicConfig(level=logging.INFO)

    # Load guidelines
    loader = GuidelineLoaderV3()
    if not loader.load_all():
        print("❌ Failed to load guidelines")
        return

    calculator = DoseCalculator(loader)

    # Test Case 1: Pyelonephritis with normal renal function
    print("\nTest Case 1: Pyelonephritis (normal renal function)")
    print("="*60)
    regimen = calculator.calculate_regimen(
        drug_ids=['ceftriaxone'],
        indication='pyelonephritis',
        crcl=90,
        patient_age=55
    )
    print(calculator.format_recommendation(regimen))

    # Test Case 2: Meningitis with vancomycin
    print("\nTest Case 2: Meningitis with vancomycin")
    print("="*60)
    regimen = calculator.calculate_regimen(
        drug_ids=['ceftriaxone', 'vancomycin'],
        indication='meningitis',
        weight=70,
        crcl=80
    )
    print(calculator.format_recommendation(regimen))

    # Test Case 3: Bacteremia with renal impairment
    print("\nTest Case 3: Bacteremia with renal impairment")
    print("="*60)
    regimen = calculator.calculate_regimen(
        drug_ids=['vancomycin'],
        indication='bacteremia_mrsa',
        crcl=25,
        weight=80,
        patient_age=75
    )
    print(calculator.format_recommendation(regimen))

    # Test Case 4: Intra-abdominal (severe PCN allergy)
    print("\nTest Case 4: Intra-abdominal with severe PCN allergy")
    print("="*60)
    regimen = calculator.calculate_regimen(
        drug_ids=['aztreonam', 'metronidazole', 'vancomycin'],
        indication='intra_abdominal',
        crcl=60
    )
    print(calculator.format_recommendation(regimen))


if __name__ == '__main__':
    main()
