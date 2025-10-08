"""
Unit tests for drug selection with allergy considerations
Critical safety tests to ensure contraindicated drugs are never recommended
"""
import pytest
import asyncio
import os
from agno_bridge_v2 import AgnoBackendBridge, InfectionCategory


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


@pytest.mark.integration
@pytest.mark.critical
@pytest.mark.allergy
class TestSeverePenicillinAllergy:
    """Critical tests for severe penicillin allergy (anaphylaxis)"""

    @pytest.mark.asyncio
    async def test_bacteremia_anaphylaxis_no_cephalosporins(self, backend_bridge):
        """
        CRITICAL: Patient with bacteremia + anaphylaxis to PCN should NOT get cephalosporins
        Expected: Aztreonam + Vancomycin
        Forbidden: Cefepime, Ceftriaxone, Piperacillin-tazobactam
        """
        patient_data = {
            'age': '88',
            'gender': 'male',
            'location': 'Ward',
            'infection_type': 'bacteremia',
            'gfr': '44',
            'allergies': 'Penicillin (anaphylaxis)',
            'inf_risks': 'MRSA colonization'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # MUST NOT contain any cephalosporins
        forbidden_drugs = ['cefepime', 'ceftriaxone', 'cefazolin', 'ceftazidime', 'cefotaxime', 'piperacillin']
        for drug in forbidden_drugs:
            assert drug not in recommendation, f"❌ CRITICAL SAFETY VIOLATION: {drug} recommended for anaphylaxis patient!"

        # SHOULD contain appropriate alternatives
        assert 'aztreonam' in recommendation or 'fluoroquinolone' in recommendation, \
            "Expected aztreonam or fluoroquinolone for severe PCN allergy"
        assert 'vancomycin' in recommendation, "Expected vancomycin for MRSA coverage"

    @pytest.mark.asyncio
    async def test_pyelonephritis_anaphylaxis_no_cephalosporins(self, backend_bridge):
        """
        CRITICAL: Pyelonephritis + anaphylaxis should get aztreonam, NOT ceftriaxone
        """
        patient_data = {
            'age': '45',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '75',
            'allergies': 'Penicillin (anaphylaxis)'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # MUST NOT contain ceftriaxone
        assert 'ceftriaxone' not in recommendation, \
            "❌ CRITICAL: Ceftriaxone recommended for anaphylaxis patient!"
        assert 'ceftr' not in recommendation, \
            "❌ CRITICAL: Ceftriaxone variant recommended for anaphylaxis patient!"

        # SHOULD contain aztreonam
        assert 'aztreonam' in recommendation, "Expected aztreonam for severe PCN allergy"

    @pytest.mark.asyncio
    async def test_meningitis_anaphylaxis_no_cephalosporins(self, backend_bridge):
        """
        CRITICAL: Meningitis + anaphylaxis is high-risk scenario
        Must use non-beta-lactam alternatives
        """
        patient_data = {
            'age': '35',
            'gender': 'male',
            'location': 'ICU',
            'infection_type': 'meningitis',
            'gfr': '90',
            'allergies': 'Penicillin (anaphylaxis, SJS)',
            'inf_risks': 'Recent neurosurgery'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # MUST NOT contain any beta-lactams
        forbidden_drugs = ['cefepime', 'ceftriaxone', 'cefotaxime', 'meropenem', 'ampicillin']
        for drug in forbidden_drugs:
            assert drug not in recommendation, \
                f"❌ CRITICAL: {drug} recommended for SJS/anaphylaxis patient!"


@pytest.mark.integration
@pytest.mark.allergy
class TestMildPenicillinAllergy:
    """Tests for mild-moderate penicillin allergy (rash only)"""

    @pytest.mark.asyncio
    async def test_bacteremia_rash_can_use_cephalosporins(self, backend_bridge):
        """
        Mild PCN allergy (rash) CAN use cephalosporins
        Expected: Cefepime or Ceftriaxone is acceptable
        """
        patient_data = {
            'age': '65',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'bacteremia',
            'gfr': '55',
            'allergies': 'Penicillin (rash)'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # For mild allergy, cephalosporins are acceptable
        # Just verify no error and confidence is reasonable
        assert result['tuhs_confidence'] >= 0.7, "Low confidence for straightforward mild allergy case"

    @pytest.mark.asyncio
    async def test_pyelonephritis_rash_gets_ceftriaxone(self, backend_bridge):
        """
        Pyelonephritis + mild PCN allergy should get ceftriaxone
        """
        patient_data = {
            'age': '50',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pyelonephritis',
            'gfr': '85',
            'allergies': 'Penicillin (rash, mild)'
        }

        result = await backend_bridge.process_request(patient_data)

        recommendation = result['tuhs_recommendation'].lower()

        # Should contain ceftriaxone for mild allergy
        assert 'ceftriaxone' in recommendation, "Expected ceftriaxone for mild PCN allergy"
        # Should NOT contain ciprofloxacin as first-line
        assert result['tuhs_recommendation'].find('ceftriaxone') < result['tuhs_recommendation'].find('ciprofloxacin') \
            if 'ciprofloxacin' in recommendation else True, \
            "Ceftriaxone should be recommended before ciprofloxacin"


@pytest.mark.integration
@pytest.mark.allergy
@pytest.mark.critical
class TestAllergyClassification:
    """Test that allergy severity is correctly classified"""

    @pytest.mark.asyncio
    async def test_anaphylaxis_treated_as_severe(self, backend_bridge):
        """Anaphylaxis must be treated as severe allergy"""
        patient_data = {
            'age': '40',
            'gender': 'male',
            'location': 'ED',
            'infection_type': 'sepsis',
            'gfr': '70',
            'allergies': 'Penicillin (anaphylaxis)'
        }

        result = await backend_bridge.process_request(patient_data)
        recommendation = result['tuhs_recommendation'].lower()

        # Must follow severe allergy protocol
        assert 'aztreonam' in recommendation or 'vancomycin' in recommendation, \
            "Anaphylaxis not treated as severe allergy"

    @pytest.mark.asyncio
    async def test_sjs_treated_as_severe(self, backend_bridge):
        """Stevens-Johnson Syndrome must be treated as severe allergy"""
        patient_data = {
            'age': '30',
            'gender': 'female',
            'location': 'Ward',
            'infection_type': 'pneumonia',
            'gfr': '90',
            'allergies': 'Penicillin (SJS)'
        }

        result = await backend_bridge.process_request(patient_data)
        recommendation = result['tuhs_recommendation'].lower()

        # Must avoid ALL beta-lactams
        forbidden = ['cef', 'ampicillin', 'piperacillin', 'meropenem']
        for drug in forbidden:
            assert drug not in recommendation, f"SJS patient given beta-lactam: {drug}"

    @pytest.mark.asyncio
    async def test_dress_treated_as_severe(self, backend_bridge):
        """DRESS syndrome must be treated as severe allergy"""
        patient_data = {
            'age': '55',
            'gender': 'male',
            'location': 'ICU',
            'infection_type': 'bacteremia',
            'gfr': '60',
            'allergies': 'Penicillin (DRESS syndrome)'
        }

        result = await backend_bridge.process_request(patient_data)
        recommendation = result['tuhs_recommendation'].lower()

        # Must avoid beta-lactams
        assert 'aztreonam' in recommendation, "DRESS not treated as severe allergy"


@pytest.mark.integration
@pytest.mark.critical
class TestNoAllergyMentionedDrugs:
    """Test that contraindicated drugs are NEVER mentioned, even to say they're contraindicated"""

    @pytest.mark.asyncio
    async def test_no_mention_of_contraindicated_drugs(self, backend_bridge):
        """
        CRITICAL: Don't say "Drug X is contraindicated, use Drug Y"
        Just recommend Drug Y directly
        """
        patient_data = {
            'age': '70',
            'gender': 'male',
            'location': 'Ward',
            'infection_type': 'bacteremia',
            'gfr': '50',
            'allergies': 'Penicillin (anaphylaxis)'
        }

        result = await backend_bridge.process_request(patient_data)
        recommendation = result['tuhs_recommendation']

        # Should not contain phrases like "is contraindicated" or "should be avoided"
        # in the context of listing the drugs
        problematic_phrases = [
            'piperacillin-tazobactam is contraindicated',
            'piperacillin-tazobactam (contraindicated)',
            'cefepime is contraindicated',
            'cefepime (since',
            'avoid piperacillin',
            'avoid cefepime'
        ]

        for phrase in problematic_phrases:
            assert phrase.lower() not in recommendation.lower(), \
                f"❌ Recommendation mentions contraindicated drug: '{phrase}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'allergy'])
