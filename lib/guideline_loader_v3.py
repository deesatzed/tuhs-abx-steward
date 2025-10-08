"""
GuidelineLoader v3 - Load modular JSON guideline files

This loader reads the new modular architecture:
- guidelines/infections/*.json - Infection-specific treatment protocols
- guidelines/drugs/*.json - Individual drug properties and dosing
- guidelines/modifiers/*.json - Cross-cutting concerns (allergies, pregnancy, renal)

Architecture:
- Step 1: Load all JSON files according to loading_order in index.json
- Step 2: Validate cross-references (drug IDs exist, no orphaned references)
- Step 3: Provide query interface for downstream components

Usage:
    loader = GuidelineLoaderV3()
    loader.load_all()

    # Query infection regimens
    regimens = loader.get_infection_regimens('uti', 'pyelonephritis', 'no_allergy')

    # Query drug dosing
    dose = loader.get_drug_dose('ceftriaxone', 'pyelonephritis', crcl=55)

    # Check pregnancy safety
    safe, reason = loader.check_pregnancy_safe('ciprofloxacin', trimester=2)
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class GuidelineLoaderV3:
    """Load and query modular guideline JSON files"""

    def __init__(self, guidelines_dir: str = None):
        """
        Initialize loader

        Args:
            guidelines_dir: Path to guidelines/ directory. Defaults to ./guidelines/
        """
        if guidelines_dir is None:
            # Default to guidelines/ directory relative to project root
            project_root = Path(__file__).parent.parent
            guidelines_dir = project_root / 'guidelines'

        self.guidelines_dir = Path(guidelines_dir)
        self.index_data = {}
        self.infections = {}  # infection_id -> infection_data
        self.drugs = {}       # drug_id -> drug_data
        self.modifiers = {}   # modifier_type -> modifier_data

        logger.info(f"GuidelineLoader initialized with directory: {self.guidelines_dir}")

    def load_all(self) -> bool:
        """
        Load all guideline files according to index.json loading order

        Returns:
            True if all files loaded successfully, False otherwise
        """
        try:
            # Load index.json first
            index_path = self.guidelines_dir / 'index.json'
            if not index_path.exists():
                logger.error(f"Index file not found: {index_path}")
                return False

            with open(index_path, 'r') as f:
                self.index_data = json.load(f)

            logger.info(f"Loaded index.json version {self.index_data.get('version')}")

            # Load files according to loading_order
            loading_order = self.index_data.get('loading_order', [])

            for file_pattern in loading_order:
                if '*' in file_pattern:
                    # Handle wildcard patterns (e.g., infections/*.json)
                    self._load_pattern(file_pattern)
                else:
                    # Load single file
                    self._load_file(file_pattern)

            # Validate cross-references
            validation_errors = self._validate_cross_references()
            if validation_errors:
                logger.warning(f"Validation errors found: {validation_errors}")

            logger.info(f"Loaded {len(self.infections)} infections, {len(self.drugs)} drugs, {len(self.modifiers)} modifiers")
            return True

        except Exception as e:
            logger.error(f"Error loading guidelines: {e}", exc_info=True)
            return False

    def _load_pattern(self, pattern: str):
        """Load all files matching a wildcard pattern"""
        # Convert pattern like "infections/*.json" to actual paths
        if pattern.startswith('modifiers/'):
            base_dir = self.guidelines_dir / 'modifiers'
            file_type = 'modifier'
        elif pattern.startswith('infections/'):
            base_dir = self.guidelines_dir / 'infections'
            file_type = 'infection'
        elif pattern.startswith('drugs/'):
            base_dir = self.guidelines_dir / 'drugs'
            file_type = 'drug'
        else:
            logger.warning(f"Unknown pattern type: {pattern}")
            return

        # Find all .json files in directory
        if base_dir.exists():
            for file_path in base_dir.glob('*.json'):
                relative_path = f"{file_type}s/{file_path.name}"
                self._load_file(relative_path)

    def _load_file(self, relative_path: str):
        """Load a single JSON file"""
        file_path = self.guidelines_dir / relative_path

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Categorize by file type
            if relative_path.startswith('modifiers/'):
                modifier_name = file_path.stem  # e.g., 'allergy_rules'
                self.modifiers[modifier_name] = data
                logger.debug(f"Loaded modifier: {modifier_name}")

            elif relative_path.startswith('infections/'):
                infection_id = file_path.stem  # e.g., 'uti'
                self.infections[infection_id] = data
                logger.debug(f"Loaded infection: {infection_id}")

            elif relative_path.startswith('drugs/'):
                drug_id = file_path.stem  # e.g., 'ceftriaxone'
                self.drugs[drug_id] = data
                logger.debug(f"Loaded drug: {drug_id}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}", exc_info=True)

    def _validate_cross_references(self) -> List[str]:
        """
        Validate that all drug IDs referenced in infection files exist in drugs/

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        # Check all drug IDs in infection regimens
        for infection_id, infection_data in self.infections.items():
            categories = infection_data.get('categories', [])
            for category in categories:
                regimens = category.get('regimens', [])
                for regimen in regimens:
                    drugs = regimen.get('drugs', [])
                    for drug_id in drugs:
                        if drug_id not in self.drugs:
                            error_msg = f"Infection '{infection_id}' references unknown drug '{drug_id}'"
                            errors.append(error_msg)
                            logger.warning(error_msg)

        return errors

    def get_infection_regimens(
        self,
        infection_type: str,
        subcategory: Optional[str] = None,
        allergy_status: str = 'no_allergy'
    ) -> List[Dict[str, Any]]:
        """
        Get treatment regimens for a specific infection

        Args:
            infection_type: e.g., 'uti', 'pneumonia', 'intra_abdominal'
            subcategory: e.g., 'pyelonephritis', 'CAP', 'peritonitis' (optional)
            allergy_status: 'no_allergy', 'mild_pcn', 'severe_pcn'

        Returns:
            List of regimen dictionaries with drug IDs and metadata
        """
        if infection_type not in self.infections:
            logger.warning(f"Unknown infection type: {infection_type}")
            return []

        infection_data = self.infections[infection_type]
        categories = infection_data.get('categories', [])

        # Filter by subcategory if provided
        if subcategory:
            categories = [c for c in categories if subcategory.lower() in c.get('category', '').lower()]

        # Extract regimens matching allergy status
        matching_regimens = []
        for category in categories:
            regimens = category.get('regimens', [])
            for regimen in regimens:
                if regimen.get('allergy_status') == allergy_status:
                    # Add category context to regimen
                    regimen_with_context = regimen.copy()
                    regimen_with_context['category'] = category.get('category')
                    regimen_with_context['route'] = category.get('route', regimen.get('route'))
                    regimen_with_context['duration'] = regimen.get('duration', category.get('duration'))
                    matching_regimens.append(regimen_with_context)

        return matching_regimens

    def get_drug_dose(
        self,
        drug_id: str,
        indication: str,
        crcl: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get dosing information for a specific drug and indication

        Args:
            drug_id: e.g., 'ceftriaxone', 'vancomycin'
            indication: e.g., 'pyelonephritis', 'meningitis', 'bacteremia_mrsa'
            crcl: Creatinine clearance in mL/min (optional, for renal adjustment)

        Returns:
            Dictionary with dose, frequency, route, monitoring, notes
            Returns None if drug not found
        """
        if drug_id not in self.drugs:
            logger.warning(f"Unknown drug: {drug_id}")
            return None

        drug_data = self.drugs[drug_id]
        dosing = drug_data.get('dosing', {})
        by_indication = dosing.get('by_indication', {})

        # Get base dose for indication
        if indication not in by_indication:
            # Try to find partial match (e.g., 'bacteremia' matches 'bacteremia_mrsa')
            matching_indications = [ind for ind in by_indication.keys() if indication in ind]
            if matching_indications:
                indication = matching_indications[0]
            else:
                logger.warning(f"No dosing found for {drug_id} + {indication}")
                return None

        dose_info = by_indication[indication].copy()

        # Apply renal adjustment if needed
        if crcl is not None:
            renal_adjustment = self._get_renal_adjustment(drug_id, crcl)
            if renal_adjustment:
                dose_info['renal_adjusted'] = True
                dose_info['original_dose'] = dose_info.get('dose')
                dose_info.update(renal_adjustment)

        # Add drug metadata
        dose_info['drug_id'] = drug_id
        dose_info['drug_name'] = drug_data.get('drug_name', drug_id)
        dose_info['class'] = drug_data.get('class')

        return dose_info

    def _get_renal_adjustment(self, drug_id: str, crcl: float) -> Optional[Dict[str, Any]]:
        """
        Get renal dose adjustment for a drug based on CrCl

        Args:
            drug_id: Drug identifier
            crcl: Creatinine clearance in mL/min

        Returns:
            Dictionary with adjusted dose/frequency, or None if no adjustment needed
        """
        renal_rules = self.modifiers.get('renal_adjustment_rules', {})
        drugs_requiring_adjustment = renal_rules.get('drugs_requiring_adjustment', {})

        if drug_id not in drugs_requiring_adjustment:
            return None

        drug_renal_data = drugs_requiring_adjustment[drug_id]

        if not drug_renal_data.get('adjustment_required', False):
            return None

        # Determine CrCl category and get adjusted dose
        if crcl >= 60:
            return None  # No adjustment needed
        elif crcl >= 30:
            adjusted_dose = drug_renal_data.get('crcl_30_60')
        elif crcl >= 15:
            adjusted_dose = drug_renal_data.get('crcl_15_29')
        elif crcl >= 10:
            adjusted_dose = drug_renal_data.get('crcl_10_29')
        else:
            adjusted_dose = drug_renal_data.get('crcl_lt_15') or drug_renal_data.get('crcl_lt_10')

        if adjusted_dose:
            # Parse adjusted dose string (e.g., "2 g IV q12h" -> separate fields)
            adjustment = {
                'adjusted_dose_string': adjusted_dose,
                'renal_note': drug_renal_data.get('note', 'Dose adjusted for renal impairment')
            }

            # Add monitoring requirements
            if drug_renal_data.get('monitoring'):
                adjustment['monitoring'] = drug_renal_data['monitoring']

            return adjustment

        return None

    def check_pregnancy_safe(
        self,
        drug_id: str,
        trimester: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a drug is safe in pregnancy

        Args:
            drug_id: Drug identifier
            trimester: 1, 2, or 3 (optional)

        Returns:
            Tuple of (is_safe: bool, reason: str or None)
        """
        pregnancy_rules = self.modifiers.get('pregnancy_rules', {})
        contraindicated = pregnancy_rules.get('contraindicated_antibiotics', {})

        # Check if drug is in any contraindicated class
        for drug_class, class_data in contraindicated.items():
            if drug_id in class_data.get('drugs', []):
                reason = class_data.get('reason', 'Contraindicated in pregnancy')
                severity = class_data.get('severity', 'contraindicated')
                return False, f"{severity.upper()}: {reason}"

        # Check trimester-specific guidance
        if trimester:
            trimester_key = 'first_trimester' if trimester == 1 else 'second_third_trimester'
            trimester_data = pregnancy_rules.get('trimester_specific_guidance', {}).get(trimester_key, {})

            if drug_id in trimester_data.get('avoid', []):
                return False, f"Avoid in trimester {trimester}"

        # Check drug-specific pregnancy data
        if drug_id in self.drugs:
            drug_data = self.drugs[drug_id]
            pregnancy_safe = drug_data.get('pregnancy_safe')
            if pregnancy_safe == 'contraindicated':
                return False, drug_data.get('pregnancy_notes', 'Contraindicated')
            elif pregnancy_safe and isinstance(pregnancy_safe, str) and 'avoid' in pregnancy_safe.lower():
                return False, drug_data.get('pregnancy_notes', 'Use with caution')

        # Default to safe if not explicitly contraindicated
        return True, None

    def classify_allergy_severity(self, allergy_description: str) -> str:
        """
        Classify allergy severity from free-text description

        Args:
            allergy_description: e.g., "Penicillin (rash)", "PCN - anaphylaxis"

        Returns:
            'mild', 'severe', or 'unknown'
        """
        if not allergy_description:
            return 'unknown'

        allergy_rules = self.modifiers.get('allergy_rules', {})
        classification = allergy_rules.get('allergy_classification', {})

        allergy_lower = allergy_description.lower()

        # Check severe keywords first (more specific)
        severe_keywords = classification.get('severe', {}).get('keywords', [])
        for keyword in severe_keywords:
            if keyword.lower() in allergy_lower:
                return 'severe'

        # Check mild keywords
        mild_keywords = classification.get('mild', {}).get('keywords', [])
        for keyword in mild_keywords:
            if keyword.lower() in allergy_lower:
                return 'mild'

        return 'unknown'

    def get_critical_rules(self, infection_type: str) -> List[str]:
        """
        Get critical rules for a specific infection type

        Args:
            infection_type: e.g., 'uti', 'pneumonia'

        Returns:
            List of critical rule strings
        """
        if infection_type not in self.index_data.get('infections', {}):
            return []

        infection_index = self.index_data['infections'][infection_type]
        return infection_index.get('critical_rules', [])

    def get_all_drug_ids(self) -> List[str]:
        """Get list of all available drug IDs"""
        return list(self.drugs.keys())

    def get_all_infection_types(self) -> List[str]:
        """Get list of all available infection types"""
        return list(self.infections.keys())


# Convenience function for testing
def main():
    """Test loader functionality"""
    logging.basicConfig(level=logging.INFO)

    loader = GuidelineLoaderV3()

    if not loader.load_all():
        print("❌ Failed to load guidelines")
        return

    print(f"\n✅ Successfully loaded guidelines")
    print(f"   Infections: {loader.get_all_infection_types()}")
    print(f"   Drugs: {loader.get_all_drug_ids()}")
    print(f"   Modifiers: {list(loader.modifiers.keys())}")

    # Test queries
    print("\n📋 Test Query 1: Pyelonephritis regimens")
    regimens = loader.get_infection_regimens('uti', 'pyelonephritis', 'no_allergy')
    for regimen in regimens:
        print(f"   {regimen}")

    print("\n📋 Test Query 2: Ceftriaxone dosing for pyelonephritis")
    dose = loader.get_drug_dose('ceftriaxone', 'pyelonephritis')
    print(f"   {dose}")

    print("\n📋 Test Query 3: Ceftriaxone dosing for meningitis")
    dose = loader.get_drug_dose('ceftriaxone', 'meningitis')
    print(f"   {dose}")

    print("\n📋 Test Query 4: Vancomycin with renal impairment")
    dose = loader.get_drug_dose('vancomycin', 'bacteremia_mrsa', crcl=25)
    print(f"   {dose}")

    print("\n📋 Test Query 5: Ciprofloxacin pregnancy safety")
    safe, reason = loader.check_pregnancy_safe('ciprofloxacin')
    print(f"   Safe: {safe}, Reason: {reason}")

    print("\n📋 Test Query 6: Allergy classification")
    print(f"   'Penicillin (rash)' -> {loader.classify_allergy_severity('Penicillin (rash)')}")
    print(f"   'PCN - anaphylaxis' -> {loader.classify_allergy_severity('PCN - anaphylaxis')}")

    print("\n📋 Test Query 7: Critical rules for UTI")
    rules = loader.get_critical_rules('uti')
    for rule in rules:
        print(f"   - {rule}")


if __name__ == '__main__':
    main()
