"""
End-to-End Test Scenarios
Real-world clinical scenarios testing the complete workflow
"""
import pytest
import asyncio
import os
from agno_bridge_v2 import AgnoBackendBridge


@pytest.fixture
def api_key():
    """Get API key from environment"""
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return key


@pytest.fixture
def backend_bridge(api_key):
    """Create backend bridge instance"""
    return AgnoBackendBridge(api_key=api_key)


@pytest.mark.e2e
@pytest.mark.critical
class TestCriticalClinicalScenarios:
    """E2E tests for critical clinical scenarios that must work correctly"""

    @pytest.mark.asyncio
    async def test_scenario_1_pyelonephritis_no_allergy(self, backend_bridge):
        """
        Scenario 1: Simple pyelonephritis, no allergies
        Expected: Ceftriaxone IV (NOT ciprofloxacin)
        """
        patient_data = {
            'age': '35',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '85',
            'allergies': 'None'
        }

        result = await backend_bridge.process_request(patient_data)

        assert result['category'] == 'pyelonephritis'
        assert result['tuhs_confidence'] >= 0.8
        recommendation = result['tuhs_recommendation'].lower()

        # PRIMARY CHECK: Ceftriaxone should be recommended
        assert 'ceftriaxone' in recommendation, "❌ Missing ceftriaxone for simple pyelonephritis"

        # SAFETY CHECK: Ciprofloxacin should NOT be first-line
        if 'ciprofloxacin' in recommendation:
            ceftriaxone_pos = recommendation.find('ceftriaxone')
            cipro_pos = recommendation.find('ciprofloxacin')
            assert ceftriaxone_pos < cipro_pos, \
                "❌ Ciprofloxacin mentioned before ceftriaxone"

    @pytest.mark.asyncio
    async def test_scenario_2_bacteremia_mrsa_anaphylaxis(self, backend_bridge):
        """
        Scenario 2: Bacteremia with MRSA colonization + severe PCN allergy
        Expected: Vancomycin + Aztreonam
        Forbidden: Any cephalosporins or penicillins
        """
        patient_data = {
            'age': '88',
            'gender': 'male',
            'location': 'Ward',
            'infection_type': 'bacteremia',
            'gfr': '44',
            'allergies': 'Penicillin (anaphylaxis)',
            'inf_risks': 'MRSA colonization, recent surgery',
            'prior_resistance': 'MRSA positive 3 months ago'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # MUST HAVE: Vancomycin for MRSA
        assert 'vancomycin' in recommendation, "❌ Missing vancomycin for MRSA coverage"

        # MUST HAVE: Aztreonam for gram-negative coverage (severe allergy)
        assert 'aztreonam' in recommendation, "❌ Missing aztreonam for severe PCN allergy"

        # MUST NOT HAVE: Any cephalosporins
        forbidden = ['cefepime', 'ceftriaxone', 'cefazolin', 'piperacillin']
        for drug in forbidden:
            assert drug not in recommendation, \
                f"❌ CRITICAL SAFETY VIOLATION: {drug} for anaphylaxis patient!"

    @pytest.mark.asyncio
    async def test_scenario_3_meningitis_no_allergy(self, backend_bridge):
        """
        Scenario 3: Bacterial meningitis, no allergies
        Expected: Vancomycin + Ceftriaxone (higher doses for meningitis)
        Note: Dosing verification will be in Step 2 tests
        """
        patient_data = {
            'age': '45',
            'gender': 'male',
            'location': 'ICU',
            'infection_type': 'meningitis',
            'gfr': '90',
            'allergies': 'None',
            'inf_risks': 'Acute onset, fever, altered mental status'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # MUST HAVE: Both vancomycin and ceftriaxone
        assert 'vancomycin' in recommendation, "❌ Missing vancomycin for meningitis"
        assert 'ceftriaxone' in recommendation, "❌ Missing ceftriaxone for meningitis"

    @pytest.mark.asyncio
    async def test_scenario_4_pneumonia_ward(self, backend_bridge):
        """
        Scenario 4: Community-acquired pneumonia, ward patient
        Expected: Ceftriaxone + Azithromycin (or doxycycline)
        """
        patient_data = {
            'age': '65',
            'gender': 'male',
            'location': 'Ward',
            'infection_type': 'pneumonia',
            'gfr': '75',
            'allergies': 'None',
            'inf_risks': 'Community-acquired, no recent hospitalization'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # Should have beta-lactam coverage
        assert any(drug in recommendation for drug in ['ceftriaxone', 'ampicillin']), \
            "Missing beta-lactam for CAP"

        # Should have atypical coverage
        assert any(drug in recommendation for drug in ['azithromycin', 'doxycycline']), \
            "Missing atypical coverage for CAP"

    @pytest.mark.asyncio
    async def test_scenario_5_pregnant_pyelonephritis(self, backend_bridge):
        """
        Scenario 5: Pregnant patient with pyelonephritis
        Expected: Ceftriaxone IV (safe in pregnancy)
        Forbidden: Fluoroquinolones, TMP/SMX
        """
        patient_data = {
            'age': '28',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '95',
            'allergies': 'None',
            'inf_risks': 'Pregnancy - 24 weeks gestation'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # MUST HAVE: Ceftriaxone (safe in pregnancy)
        assert 'ceftriaxone' in recommendation, "❌ Missing ceftriaxone for pregnant patient"

        # MUST NOT HAVE: Fluoroquinolones (contraindicated in pregnancy)
        forbidden_in_pregnancy = ['ciprofloxacin', 'levofloxacin', 'moxifloxacin']
        for drug in forbidden_in_pregnancy:
            assert drug not in recommendation, \
                f"❌ CRITICAL: {drug} recommended in pregnancy!"

        # SHOULD MENTION: Pregnancy safety
        assert 'pregnan' in recommendation, "Should address pregnancy safety"

    @pytest.mark.asyncio
    async def test_scenario_6_icu_sepsis_shock(self, backend_bridge):
        """
        Scenario 6: Septic shock in ICU, unknown source
        Expected: Broad-spectrum coverage (pip-tazo or cefepime + vancomycin + metronidazole)
        """
        patient_data = {
            'age': '70',
            'gender': 'female',
            'location': 'ICU',
            'infection_type': 'sepsis',
            'gfr': '35',
            'allergies': 'None',
            'inf_risks': 'Septic shock, unknown source, intubated'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # Need broad-spectrum coverage
        assert any(drug in recommendation for drug in ['piperacillin', 'cefepime', 'meropenem']), \
            "Missing broad-spectrum beta-lactam for septic shock"

        # Need MRSA coverage
        assert 'vancomycin' in recommendation, "Missing vancomycin for septic shock"

        # Need anaerobic coverage
        assert 'metronidazole' in recommendation or 'piperacillin' in recommendation, \
            "Missing anaerobic coverage"


@pytest.mark.e2e
class TestEdgeCases:
    """E2E tests for edge cases and complex scenarios"""

    @pytest.mark.asyncio
    async def test_dialysis_patient(self, backend_bridge):
        """Test patient on hemodialysis"""
        patient_data = {
            'age': '75',
            'gender': 'male',
            'location': 'Ward',
            'infection_type': 'bacteremia',
            'gfr': '10',
            'allergies': 'None',
            'inf_risks': 'On hemodialysis MWF, central line'
        }

        result = await backend_bridge.process_request(patient_data)

        # Should succeed and have reasonable confidence
        assert result['tuhs_confidence'] >= 0.6, "Very low confidence for HD patient"

        # Should recommend ID consultation for complex case
        recommendation = result['tuhs_recommendation'].lower()
        # Either has specific HD dosing or recommends consultation
        assert 'hemodialysis' in recommendation or 'dialysis' in recommendation or 'id' in recommendation

    @pytest.mark.asyncio
    async def test_multiple_drug_allergies(self, backend_bridge):
        """Test patient with multiple drug allergies"""
        patient_data = {
            'age': '55',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pneumonia',
            'gfr': '60',
            'allergies': 'Penicillin (anaphylaxis), Sulfa (rash), Vancomycin (red man syndrome)'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # Should work around all allergies
        # No penicillins/cephalosporins, no sulfa drugs, no vancomycin
        forbidden = ['penicillin', 'ceftriaxone', 'cefepime', 'trimethoprim', 'sulfamethoxazole', 'vancomycin']
        for drug in forbidden:
            assert drug not in recommendation, f"Recommended allergic drug: {drug}"

    @pytest.mark.asyncio
    async def test_very_low_gfr(self, backend_bridge):
        """Test patient with severe renal impairment"""
        patient_data = {
            'age': '80',
            'gender': 'male',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '15',
            'allergies': 'None'
        }

        result = await backend_bridge.process_request(patient_data)

        # After dosing separation, Step 1 focuses on drug selection only
        # Renal adjustments will be handled in Step 2 (dosing calculator)
        # Just verify the request succeeds with reasonable confidence
        assert result['tuhs_confidence'] >= 0.7, "Should have reasonable confidence for severe renal impairment case"
        recommendation = result['tuhs_recommendation'].lower()
        assert 'ceftriaxone' in recommendation, "Should recommend appropriate antibiotic for pyelonephritis"


@pytest.mark.e2e
@pytest.mark.slow
class TestConsistency:
    """Test that similar cases produce consistent results"""

    @pytest.mark.asyncio
    async def test_same_input_consistent_output(self, backend_bridge):
        """Test that identical input produces consistent results"""
        patient_data = {
            'age': '50',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '70',
            'allergies': 'None'
        }

        # Run twice
        result1 = await backend_bridge.process_request(patient_data)
        result2 = await backend_bridge.process_request(patient_data)

        # Should get same category
        assert result1['category'] == result2['category']

        # Should have similar confidence (within 10%)
        assert abs(result1['tuhs_confidence'] - result2['tuhs_confidence']) < 0.1

    @pytest.mark.asyncio
    async def test_similar_cases_similar_drugs(self, backend_bridge):
        """Test that similar cases get similar drug recommendations"""
        # Two similar pyelonephritis cases, slightly different ages
        patient1 = {
            'age': '35',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '85',
            'allergies': 'None'
        }

        patient2 = {
            'age': '38',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '80',
            'allergies': 'None'
        }

        result1 = await backend_bridge.process_request(patient1)
        result2 = await backend_bridge.process_request(patient2)

        # Both should recommend ceftriaxone
        assert 'ceftriaxone' in result1['tuhs_recommendation'].lower()
        assert 'ceftriaxone' in result2['tuhs_recommendation'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])
