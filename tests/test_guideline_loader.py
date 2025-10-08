"""
Unit tests for TUHSGuidelineLoader
Tests JSON loading, parsing, and instruction generation
"""
import pytest
import json
import tempfile
import os
from agno_bridge_v2 import TUHSGuidelineLoader, InfectionCategory


class TestGuidelineLoader:
    """Test suite for TUHSGuidelineLoader"""

    @pytest.fixture
    def temp_selection_json(self):
        """Create temporary selection JSON for testing"""
        data = {
            "document_title": "Test Selection Guidelines",
            "document_type": "Antibiotic Selection Guidelines",
            "origin_date": "2025-01",
            "caveat": "Test data",
            "general_instructions": ["Test instruction 1", "Test instruction 2"],
            "infection_guidelines": [
                {
                    "infection": "Test Infection",
                    "sub_sections": [
                        {
                            "type": "Test Type",
                            "empiric_regimens": [
                                {
                                    "pcp_allergy_status": "NO Penicillin (PCN) ALLERGY",
                                    "regimen": ["Drug A", "Drug B"]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(data, f)
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def temp_dosing_json(self):
        """Create temporary dosing JSON for testing"""
        data = {
            "document_title": "Test Dosing Guidelines",
            "document_type": "Antibiotic Dosing Guidelines",
            "dosing_and_renal_adjustment": {
                "calculation_notes": {"test": "notes"},
                "renal_dosing_table": [
                    {
                        "drug": "Test Drug IV",
                        "ed_once_dose": "10 mg/kg",
                        "crcl_gt_50": "10 mg/kg q8h",
                        "crcl_50_30": "10 mg/kg q12h"
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(data, f)
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    @pytest.mark.unit
    def test_loader_initialization(self, temp_selection_json, temp_dosing_json):
        """Test loader initializes correctly with split files"""
        loader = TUHSGuidelineLoader(
            selection_json=temp_selection_json,
            dosing_json=temp_dosing_json
        )

        assert loader.selection_guidelines is not None
        assert loader.dosing_guidelines is not None
        assert loader.guidelines is not None

    @pytest.mark.unit
    def test_loader_with_real_files(self):
        """Test loader works with actual ABX_Selection.json and ABX_Dosing.json"""
        loader = TUHSGuidelineLoader()

        assert len(loader.selection_guidelines.get('infection_guidelines', [])) > 0
        assert len(loader.dosing_guidelines.get('dosing_and_renal_adjustment', {}).get('renal_dosing_table', [])) > 0

    @pytest.mark.unit
    def test_legacy_fallback(self):
        """Test loader falls back to legacy ABXguideInp.json if split files missing"""
        loader = TUHSGuidelineLoader(
            selection_json="nonexistent.json",
            dosing_json="nonexistent.json",
            legacy_json="ABXguideInp.json"
        )

        assert loader.guidelines is not None
        assert 'infection_guidelines' in loader.guidelines

    @pytest.mark.unit
    def test_get_infection_guideline(self):
        """Test retrieving specific infection guideline"""
        loader = TUHSGuidelineLoader()

        pneumonia = loader.get_infection_guideline("Pneumonia")
        assert pneumonia is not None
        assert pneumonia.get('infection') == 'Pneumonia'

    @pytest.mark.unit
    def test_build_agent_instructions_pyelonephritis(self):
        """Test instruction generation for pyelonephritis"""
        loader = TUHSGuidelineLoader()

        instructions = loader.build_agent_instructions('Urinary Tract', subsection_filter='Pyelonephritis')

        assert len(instructions) > 50
        # Check for critical instructions
        assert any('PYELONEPHRITIS-SPECIFIC WARNINGS' in line for line in instructions)
        assert any('NEVER use Ciprofloxacin' in line for line in instructions)
        assert any('Ceftriaxone IV is MANDATORY' in line for line in instructions)
        assert any('DO NOT specify exact doses' in line for line in instructions)

    @pytest.mark.unit
    @pytest.mark.allergy
    def test_allergy_instructions_included(self):
        """Test that allergy handling instructions are included"""
        loader = TUHSGuidelineLoader()

        instructions = loader.build_agent_instructions('Sepsis')

        allergy_section = [line for line in instructions if 'ALLERGY HANDLING' in line or 'ANAPHYLAXIS' in line]
        assert len(allergy_section) > 0
        assert any('ANAPHYLAXIS = SEVERE ALLERGY' in line for line in instructions)
        assert any('Cefepime, Ceftriaxone, Cefazolin = ALL CEPHALOSPORINS = CONTRAINDICATED' in line for line in instructions)

    @pytest.mark.unit
    def test_pregnancy_instructions_separated(self):
        """Test that pregnancy instructions are separated by infection type"""
        loader = TUHSGuidelineLoader()

        # Pyelonephritis should have pyelonephritis-specific pregnancy guidance
        pyelo_instructions = loader.build_agent_instructions('Urinary Tract', subsection_filter='Pyelonephritis')
        assert any('PYELONEPHRITIS-SPECIFIC PREGNANCY GUIDANCE' in line for line in pyelo_instructions)
        assert any('Ceftriaxone IV is MANDATORY first-line' in line for line in pyelo_instructions)

        # Cystitis should have cystitis-specific pregnancy guidance
        cystitis_instructions = loader.build_agent_instructions('Urinary Tract', subsection_filter='Cystitis')
        assert any('CYSTITIS-SPECIFIC PREGNANCY GUIDANCE' in line for line in cystitis_instructions)

    @pytest.mark.unit
    def test_dosing_separation_instruction(self):
        """Test that dosing separation instructions are present"""
        loader = TUHSGuidelineLoader()

        instructions = loader.build_agent_instructions('Pneumonia')

        dosing_section = [line for line in instructions if 'DRUG SELECTION ONLY' in line or 'DO NOT specify' in line]
        assert len(dosing_section) > 0
        assert any('DO NOT specify exact doses, frequencies, or durations' in line for line in instructions)


class TestInfectionCategory:
    """Test InfectionCategory enum"""

    @pytest.mark.unit
    def test_infection_categories_exist(self):
        """Test that all infection categories are defined"""
        assert hasattr(InfectionCategory, 'PNEUMONIA')
        assert hasattr(InfectionCategory, 'CYSTITIS')
        assert hasattr(InfectionCategory, 'PYELONEPHRITIS')
        assert hasattr(InfectionCategory, 'BACTEREMIA_SEPSIS')
        assert hasattr(InfectionCategory, 'MENINGITIS')
        assert hasattr(InfectionCategory, 'SKIN_SOFT_TISSUE')


@pytest.mark.unit
@pytest.mark.critical
class TestJSONFileIntegrity:
    """Test that JSON files are valid and complete"""

    def test_abx_selection_json_valid(self):
        """Test ABX_Selection.json is valid JSON"""
        with open('ABX_Selection.json', 'r') as f:
            data = json.load(f)

        assert 'infection_guidelines' in data
        assert isinstance(data['infection_guidelines'], list)
        assert len(data['infection_guidelines']) > 0

    def test_abx_dosing_json_valid(self):
        """Test ABX_Dosing.json is valid JSON"""
        with open('ABX_Dosing.json', 'r') as f:
            data = json.load(f)

        assert 'dosing_and_renal_adjustment' in data
        assert 'renal_dosing_table' in data['dosing_and_renal_adjustment']
        assert isinstance(data['dosing_and_renal_adjustment']['renal_dosing_table'], list)

    def test_legacy_json_valid(self):
        """Test ABXguideInp.json is still valid for backward compatibility"""
        with open('ABXguideInp.json', 'r') as f:
            data = json.load(f)

        assert 'infection_guidelines' in data
        assert 'dosing_and_renal_adjustment' in data

    def test_infection_types_coverage(self):
        """Test that all expected infection types are present"""
        with open('ABX_Selection.json', 'r') as f:
            data = json.load(f)

        infection_types = [item['infection'] for item in data['infection_guidelines']]

        expected_types = ['Pneumonia', 'Urinary Tract', 'Sepsis']
        for expected in expected_types:
            assert any(expected in inf_type for inf_type in infection_types), f"Missing {expected}"

    def test_dosing_table_has_required_columns(self):
        """Test dosing table has all required columns"""
        with open('ABX_Dosing.json', 'r') as f:
            data = json.load(f)

        required_columns = ['drug', 'crcl_gt_50', 'crcl_50_30', 'crcl_29_10']

        for entry in data['dosing_and_renal_adjustment']['renal_dosing_table']:
            for col in required_columns:
                assert col in entry, f"Missing required column {col} in entry {entry.get('drug')}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
