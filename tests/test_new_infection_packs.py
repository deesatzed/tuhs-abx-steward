"""Tests for DKR-ported empiric infection packs (TUH 2025-04-02)."""

import json
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.guideline_loader_v3 import GuidelineLoaderV3

NEW_INFECTION_CODES = [
    "bite_wounds",
    "central_line_infection",
    "infected_diabetic_wound",
    "neutropenic_fever",
    "sepsis_unknown_origin",
]

INDEX_ONLY_EXISTING = ["ssti", "cns", "bone_joint", "endocarditis"]

# Named in DKR regimens/adjuncts but no monograph in guidelines/drugs/
DRUGS_WITHOUT_MONOGRAPH = {"micafungin", "tobramycin"}


@pytest.fixture
def loader():
    loader = GuidelineLoaderV3()
    success = loader.load_all()
    assert success, "Failed to load guidelines"
    return loader


class TestNewInfectionPacksLoad:
    def test_load_all_succeeds(self, loader):
        assert loader.load_all() is True

    def test_new_infection_codes_loaded(self, loader):
        for code in NEW_INFECTION_CODES:
            assert code in loader.infections, f"Missing infection: {code}"
            data = loader.infections[code]
            assert data.get("infection_code") == code
            assert data.get("version") == "3.0.0"
            assert data.get("last_updated") == "2026-08-28"
            assert data.get("categories"), f"{code} has no categories"

    def test_get_infection_regimens_no_allergy(self, loader):
        for code in NEW_INFECTION_CODES:
            regimens = loader.get_infection_regimens(code, allergy_status="no_allergy")
            assert len(regimens) > 0, f"No no_allergy regimens for {code}"
            for regimen in regimens:
                assert regimen.get("drugs"), f"{code} regimen missing drugs"
                assert regimen.get("allergy_status") == "no_allergy"

    def test_get_infection_regimens_mild_and_severe_pcn(self, loader):
        for code in NEW_INFECTION_CODES:
            mild = loader.get_infection_regimens(code, allergy_status="mild_pcn_allergy")
            severe = loader.get_infection_regimens(code, allergy_status="severe_pcn_allergy")
            assert len(mild) > 0, f"No mild_pcn_allergy regimens for {code}"
            assert len(severe) > 0, f"No severe_pcn_allergy regimens for {code}"

    def test_index_registers_new_and_previously_missing(self, loader):
        index_infections = loader.index_data.get("infections", {})
        for code in NEW_INFECTION_CODES + INDEX_ONLY_EXISTING:
            assert code in index_infections, f"index.json missing {code}"
            entry = index_infections[code]
            assert entry.get("status") == "active", f"{code} not active in index"
            expected_file = f"infections/{code}.json"
            assert entry.get("file") == expected_file, f"{code} file mismatch: {entry.get('file')}"

    def test_stale_ssti_filename_fixed(self, loader):
        infections = loader.index_data["infections"]
        assert "skin_soft_tissue" not in infections
        assert infections["ssti"]["file"] == "infections/ssti.json"
        assert infections["ssti"]["status"] == "active"
        ssti_path = project_root / "guidelines" / "infections" / "ssti.json"
        assert ssti_path.exists()

    def test_mapped_primary_drugs_match_dkr_no_allergy(self, loader):
        """Spot-check first-line no_allergy drugs against DKR rank-1 primaryDrugs."""
        expected = {
            "bite_wounds": {"amoxicillin_clavulanate", "ampicillin_sulbactam"},
            "central_line_infection": {"cefepime", "vancomycin"},
            "infected_diabetic_wound": {"vancomycin", "ceftriaxone", "piperacillin_tazobactam"},
            "neutropenic_fever": {"cefepime"},
            "sepsis_unknown_origin": {"cefepime", "metronidazole", "vancomycin"},
        }
        for code, required in expected.items():
            regimens = loader.get_infection_regimens(code, allergy_status="no_allergy")
            listed = {d for r in regimens for d in r.get("drugs", [])}
            missing = required - listed
            assert not missing, f"{code} missing expected DKR drugs {missing}; have {listed}"


class TestMissingDrugMonographs:
    """DKR named micafungin and tobramycin; do not invent monographs."""

    def test_todos_record_missing_monographs(self, loader):
        todos = loader.index_data.get("todos", [])
        blob = " ".join(todos).lower()
        for drug in DRUGS_WITHOUT_MONOGRAPH:
            assert drug in blob, f"index.json todos should mention {drug}"
            assert drug not in loader.drugs, (
                f"{drug} unexpectedly has a drug monograph; remove the TODO if a real file was added"
            )

    def test_adjuncts_named_in_new_packs(self, loader):
        clabsi = loader.infections["central_line_infection"]
        adjunct_drugs = [
            d
            for cat in clabsi["categories"]
            for adj in cat.get("conditional_adjuncts", [])
            for d in adj.get("drugs", [])
        ]
        assert "micafungin" in adjunct_drugs

        nfn = loader.infections["neutropenic_fever"]
        one_time = [
            d
            for cat in nfn["categories"]
            for ot in cat.get("one_time_doses", [])
            for d in ot.get("drugs", [])
        ]
        assert "tobramycin" in one_time

        sepsis = loader.infections["sepsis_unknown_origin"]
        one_time = [
            d
            for cat in sepsis["categories"]
            for ot in cat.get("one_time_doses", [])
            for d in ot.get("drugs", [])
        ]
        assert "tobramycin" in one_time


class TestSourcePacksPreserved:
    def test_source_packs_exist_and_are_dkr_format(self):
        src = project_root / "guidelines" / "source_packs"
        readme = (src / "README.md").read_text()
        assert "2025-04-02" in readme
        assert "not the runtime schema" in readme.lower() or "not the v3 runtime" in readme.lower()

        for name in [
            "bite_wounds.json",
            "central_line_infection.json",
            "infected_diabetic_wound.json",
            "neutropenic_fever.json",
            "sepsis_unknown_origin.json",
        ]:
            data = json.loads((src / name).read_text())
            assert "documentInfo" in data
            assert "infections" in data
            assert data["documentInfo"].get("versionDate") == "2025-04-02"

    def test_infection_cap_kept_as_documentation_only(self):
        src = project_root / "guidelines" / "source_packs" / "infection_cap.json"
        assert src.exists()
        infections_dir = project_root / "guidelines" / "infections"
        assert not (infections_dir / "infection_cap.json").exists()
        assert not (infections_dir / "cap.json").exists()
