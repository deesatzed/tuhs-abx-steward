"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import json
from typing import Dict


@pytest.fixture(scope="session")
def api_key():
    """Get API key from environment - session scoped"""
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set - skipping API tests")
    return key


@pytest.fixture(scope="session")
def test_data_dir():
    """Directory for test data files"""
    return os.path.join(os.path.dirname(__file__), 'test_data')


@pytest.fixture
def sample_patient_simple():
    """Simple patient case - no allergies, normal renal function"""
    return {
        'age': '45',
        'gender': 'female',
        'location': 'Ward',
        'infection_type': 'pyelonephritis',
        'gfr': '85',
        'allergies': 'None'
    }


@pytest.fixture
def sample_patient_severe_allergy():
    """Patient with severe penicillin allergy"""
    return {
        'age': '70',
        'gender': 'male',
        'location': 'Ward',
        'infection_type': 'bacteremia',
        'gfr': '50',
        'allergies': 'Penicillin (anaphylaxis)'
    }


@pytest.fixture
def sample_patient_pregnant():
    """Pregnant patient"""
    return {
        'age': '28',
        'gender': 'female',
        'location': 'Ward',
        'infection_type': 'pyelonephritis',
        'gfr': '95',
        'allergies': 'None',
        'inf_risks': 'Pregnancy - 26 weeks gestation'
    }


@pytest.fixture
def sample_patient_icu_sepsis():
    """ICU patient with septic shock"""
    return {
        'age': '65',
        'gender': 'male',
        'location': 'ICU',
        'infection_type': 'sepsis',
        'gfr': '35',
        'allergies': 'None',
        'inf_risks': 'Septic shock, intubated, unknown source'
    }


@pytest.fixture
def sample_patient_renal_failure():
    """Patient with severe renal impairment"""
    return {
        'age': '80',
        'gender': 'female',
        'location': 'Ward',
        'infection_type': 'bacteremia',
        'gfr': '12',
        'allergies': 'None',
        'inf_risks': 'Stage 5 CKD, not on dialysis'
    }


@pytest.fixture
def sample_patient_mrsa():
    """Patient with MRSA colonization"""
    return {
        'age': '60',
        'gender': 'male',
        'location': 'Ward',
        'infection_type': 'bacteremia',
        'gfr': '60',
        'allergies': 'None',
        'inf_risks': 'MRSA nares positive, central line'
    }


@pytest.fixture
def expected_drugs_pyelonephritis():
    """Expected drug recommendations for pyelonephritis"""
    return {
        'no_allergy': ['ceftriaxone'],
        'mild_pcn_allergy': ['ceftriaxone'],
        'severe_pcn_allergy': ['aztreonam'],
        'pregnant': ['ceftriaxone']
    }


@pytest.fixture
def expected_drugs_bacteremia():
    """Expected drug recommendations for bacteremia"""
    return {
        'no_allergy': ['cefepime', 'piperacillin-tazobactam', 'vancomycin'],
        'mild_pcn_allergy': ['cefepime', 'vancomycin'],
        'severe_pcn_allergy': ['aztreonam', 'vancomycin'],
        'mrsa': ['vancomycin']
    }


@pytest.fixture
def forbidden_drugs_by_allergy():
    """Drugs that must never be recommended for certain allergies"""
    return {
        'severe_pcn_allergy': [
            'penicillin', 'ampicillin', 'piperacillin',
            'ceftriaxone', 'cefepime', 'cefazolin',
            'ceftazidime', 'cefotaxime', 'cefuroxime'
        ],
        'pregnancy': [
            'ciprofloxacin', 'levofloxacin', 'moxifloxacin',
            'tetracycline', 'doxycycline'
        ]
    }


def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "critical: mark test as critical (must pass for deployment)"
    )
    config.addinivalue_line(
        "markers", "allergy: mark test as allergy-related safety test"
    )
    config.addinivalue_line(
        "markers", "dosing: mark test as dosing calculation test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers dynamically"""
    for item in items:
        # Add slow marker to async tests
        if 'asyncio' in item.keywords:
            item.add_marker(pytest.mark.slow)

        # Add critical marker to safety tests
        if 'allergy' in item.keywords or 'anaphylaxis' in item.name.lower():
            item.add_marker(pytest.mark.critical)


@pytest.fixture(autouse=True)
def reset_between_tests():
    """Reset any global state between tests"""
    yield
    # Cleanup code here if needed


@pytest.fixture
def mock_validation_result():
    """Mock validation result for testing"""
    return {
        "status": "APPROVED",
        "confidence": 0.95,
        "issues": [],
        "suggested_corrections": [],
        "severity": None,
        "notes": "Recommendation looks good"
    }


@pytest.fixture
def mock_validation_result_with_issues():
    """Mock validation result with issues flagged"""
    return {
        "status": "REQUIRES_REVIEW",
        "confidence": 0.4,
        "issues": [
            "Cephalosporin recommended for severe PCN allergy",
            "Missing loading dose for meningitis"
        ],
        "suggested_corrections": [
            "Use aztreonam instead of cefepime",
            "Add vancomycin loading dose 25-30 mg/kg"
        ],
        "severity": "CRITICAL",
        "notes": "Critical safety issues detected"
    }


# Performance tracking
@pytest.fixture(autouse=True)
def track_test_performance(request):
    """Track test execution time"""
    import time
    start = time.time()
    yield
    duration = time.time() - start

    if duration > 5:
        print(f"\n⚠️  Slow test: {request.node.name} took {duration:.2f}s")
