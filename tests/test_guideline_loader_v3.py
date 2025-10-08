"""
Test suite for GuidelineLoader v3

Tests cover:
- Loading all JSON files
- Cross-reference validation
- Query methods (infections, drugs, modifiers)
- Allergy classification
- Pregnancy safety checks
- Renal adjustment calculations
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.guideline_loader_v3 import GuidelineLoaderV3


@pytest.fixture
def loader():
    """Create and load GuidelineLoader instance"""
    loader = GuidelineLoaderV3()
    success = loader.load_all()
    assert success, "Failed to load guidelines"
    return loader


class TestLoading:
    """Test guideline file loading"""

    def test_load_all_files(self, loader):
        """Test that all files load successfully"""
        assert len(loader.infections) > 0, "No infection files loaded"
        assert len(loader.drugs) > 0, "No drug files loaded"
        assert len(loader.modifiers) > 0, "No modifier files loaded"

    def test_expected_infections_loaded(self, loader):
        """Test that expected infection types are loaded"""
        expected = ['uti', 'pneumonia', 'intra_abdominal', 'bacteremia', 'meningitis']
        for infection_type in expected:
            assert infection_type in loader.infections, f"Missing infection: {infection_type}"

    def test_expected_drugs_loaded(self, loader):
        """Test that expected drugs are loaded"""
        expected = ['ceftriaxone', 'aztreonam', 'piperacillin_tazobactam', 'vancomycin', 'metronidazole']
        for drug_id in expected:
            assert drug_id in loader.drugs, f"Missing drug: {drug_id}"

    def test_expected_modifiers_loaded(self, loader):
        """Test that expected modifiers are loaded"""
        expected = ['allergy_rules', 'pregnancy_rules', 'renal_adjustment_rules']
        for modifier in expected:
            assert modifier in loader.modifiers, f"Missing modifier: {modifier}"


class TestInfectionQueries:
    """Test infection guideline queries"""

    def test_get_pyelonephritis_no_allergy(self, loader):
        """Test pyelonephritis regimen without allergy"""
        regimens = loader.get_infection_regimens('uti', 'pyelonephritis', 'no_allergy')
        assert len(regimens) > 0, "No regimens found for pyelonephritis"
        assert 'ceftriaxone' in regimens[0]['drugs'], "Ceftriaxone not in pyelonephritis regimen"

    def test_get_pyelonephritis_mild_pcn_allergy(self, loader):
        """Test pyelonephritis with mild PCN allergy"""
        regimens = loader.get_infection_regimens('uti', 'pyelonephritis', 'mild_pcn_allergy')
        assert len(regimens) > 0, "No regimens found for pyelonephritis + mild PCN allergy"
        # Should still get cephalosporins
        drugs = regimens[0]['drugs']
        assert 'ceftriaxone' in drugs or 'cefepime' in drugs, "Should allow cephalosporins for mild allergy"

    def test_get_intra_abdominal_severe_pcn_allergy(self, loader):
        """Test intra-abdominal with severe PCN allergy"""
        regimens = loader.get_infection_regimens('intra_abdominal', allergy_status='severe_pcn_allergy')
        assert len(regimens) > 0, "No regimens found for intra-abdominal + severe PCN allergy"
        drugs = regimens[0]['drugs']
        assert 'aztreonam' in drugs, "Should use aztreonam for severe PCN allergy"
        assert 'metronidazole' in drugs, "Should use metronidazole for anaerobic coverage"

    def test_get_critical_rules_uti(self, loader):
        """Test critical rules for UTI"""
        rules = loader.get_critical_rules('uti')
        assert len(rules) > 0, "No critical rules found for UTI"
        # Check for pyelonephritis IV requirement
        assert any('IV' in rule for rule in rules), "Missing IV requirement rule"


class TestDrugDosing:
    """Test drug dosing queries"""

    def test_ceftriaxone_pyelonephritis(self, loader):
        """Test ceftriaxone dosing for pyelonephritis"""
        dose = loader.get_drug_dose('ceftriaxone', 'pyelonephritis')
        assert dose is not None, "No dose found for ceftriaxone + pyelonephritis"
        assert dose['dose'] == '1 g IV', "Incorrect dose for pyelonephritis"
        assert dose['frequency'] == 'q24h', "Incorrect frequency"

    def test_ceftriaxone_meningitis_higher_dose(self, loader):
        """Test ceftriaxone requires higher dose for meningitis"""
        dose = loader.get_drug_dose('ceftriaxone', 'meningitis')
        assert dose is not None, "No dose found for ceftriaxone + meningitis"
        assert dose['dose'] == '2 g IV', "Meningitis should require 2g dose"
        assert dose['frequency'] == 'q12h', "Meningitis should require q12h dosing"

    def test_vancomycin_loading_dose(self, loader):
        """Test vancomycin loading dose for severe infections"""
        dose = loader.get_drug_dose('vancomycin', 'meningitis')
        assert dose is not None, "No dose found for vancomycin + meningitis"
        assert dose.get('loading_dose'), "Meningitis should require loading dose"
        assert '25-30 mg/kg' in dose['loading_dose'], "Loading dose should be weight-based"


class TestAllergyClassification:
    """Test allergy severity classification"""

    def test_classify_mild_allergy_rash(self, loader):
        """Test classification of mild rash allergy"""
        severity = loader.classify_allergy_severity('Penicillin (rash)')
        assert severity == 'mild', "Rash only should be classified as mild"

    def test_classify_severe_allergy_anaphylaxis(self, loader):
        """Test classification of anaphylaxis"""
        severity = loader.classify_allergy_severity('Penicillin - anaphylaxis')
        assert severity == 'severe', "Anaphylaxis should be classified as severe"

    def test_classify_severe_allergy_sjs(self, loader):
        """Test classification of Stevens-Johnson syndrome"""
        severity = loader.classify_allergy_severity('PCN allergy (SJS)')
        assert severity == 'severe', "SJS should be classified as severe"


class TestPregnancySafety:
    """Test pregnancy safety checks"""

    def test_ceftriaxone_safe_pregnancy(self, loader):
        """Test ceftriaxone is safe in pregnancy"""
        safe, reason = loader.check_pregnancy_safe('ceftriaxone')
        assert safe, "Ceftriaxone should be safe in pregnancy"

    def test_aztreonam_safe_pregnancy(self, loader):
        """Test aztreonam is safe in pregnancy"""
        safe, reason = loader.check_pregnancy_safe('aztreonam')
        assert safe, "Aztreonam should be safe in pregnancy"


class TestCriticalSafetyRules:
    """Test critical safety rules from past bugs"""

    def test_pyelonephritis_never_oral_ciprofloxacin(self, loader):
        """Test pyelonephritis regimens never include oral ciprofloxacin"""
        regimens = loader.get_infection_regimens('uti', 'pyelonephritis', 'no_allergy')
        for regimen in regimens:
            route = regimen.get('route')
            assert route == 'IV', "Pyelonephritis must be IV"
            # Ensure ciprofloxacin is not first-line
            drugs = regimen.get('drugs', [])
            # Ceftriaxone should be first-line, not cipro
            if drugs:
                assert drugs[0] == 'ceftriaxone', "Ceftriaxone should be first-line for pyelonephritis"

    def test_severe_pcn_allergy_no_cephalosporins(self, loader):
        """Test severe PCN allergy never gets cephalosporins"""
        # Check intra-abdominal with severe allergy
        regimens = loader.get_infection_regimens('intra_abdominal', allergy_status='severe_pcn_allergy')
        cephalosporins = ['ceftriaxone', 'cefepime', 'cefazolin']
        for regimen in regimens:
            drugs = regimen.get('drugs', [])
            for drug in drugs:
                assert drug not in cephalosporins, f"Severe PCN allergy should not get {drug}"

    def test_mild_pcn_allergy_can_use_cephalosporins(self, loader):
        """Test mild PCN allergy (rash) CAN use cephalosporins"""
        regimens = loader.get_infection_regimens('uti', 'pyelonephritis', 'mild_pcn_allergy')
        assert len(regimens) > 0, "Should have regimens for mild PCN allergy"
        # Should allow ceftriaxone or other cephalosporins
        cephalosporins_allowed = False
        for regimen in regimens:
            drugs = regimen.get('drugs', [])
            if any(drug in ['ceftriaxone', 'cefepime'] for drug in drugs):
                cephalosporins_allowed = True
                break
        assert cephalosporins_allowed, "Mild PCN allergy should allow cephalosporins"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
