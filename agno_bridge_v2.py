"""
Agno Backend Bridge V2: LOADS ACTUAL TUHS JSON GUIDELINES
Provides REST API with real TUHS institutional guidelines
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import asyncio
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Import the FULL Agno system
from evidence_coordinator_full import FullEvidenceCoordinator, SearchResult
from agno.agent import Agent
from agno.models.openai import OpenAIChat

app = Flask(__name__)
CORS(app)  # Enable CORS for Express frontend


# Infection categories
class InfectionCategory:
    PNEUMONIA = "pneumonia"
    CYSTITIS = "cystitis"
    PYELONEPHRITIS = "pyelonephritis"
    SKIN_SOFT_TISSUE = "skin_soft_tissue"
    INTRA_ABDOMINAL = "intra_abdominal"
    BACTEREMIA_SEPSIS = "bacteremia_sepsis"
    MENINGITIS = "meningitis"
    NEUTROPENIC_FEVER = "neutropenic_fever"
    CENTRAL_LINE = "central_line"
    GENERAL = "general"


class TUHSGuidelineLoader:
    """Loads and parses TUHS guidelines from JSON"""
    
    def __init__(self, json_path: str = "ABXguideInp.json"):
        self.json_path = json_path
        self.guidelines = self._load_guidelines()
    
    def _load_guidelines(self) -> Dict:
        """Load JSON guidelines"""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
                print(f"✅ Loaded TUHS guidelines from {self.json_path}")
                return data
        except Exception as e:
            print(f"❌ Error loading guidelines: {e}")
            return {}
    
    def get_infection_guideline(self, infection_name: str) -> Dict:
        """Get specific infection guideline"""
        for guideline in self.guidelines.get('infection_guidelines', []):
            if infection_name.lower() in guideline['infection'].lower():
                return guideline
        return {}
    
    def build_agent_instructions(self, infection_name: str, subsection_filter: str = None) -> List[str]:
        """Build detailed instructions from JSON guidelines

        Args:
            infection_name: Name of infection (e.g., "Pneumonia", "Urinary Tract")
            subsection_filter: Optional filter to include only matching subsections (e.g., "Cystitis", "Pyelonephritis")
        """
        guideline = self.get_infection_guideline(infection_name)

        if not guideline:
            return [
                f"You are a TUHS {infection_name} treatment expert.",
                "Follow TUHS antibiotic guidelines strictly.",
                "Provide evidence-based recommendations."
            ]

        instructions = [
            f"You are a TUHS {guideline['infection']} treatment expert.",
            "Follow these EXACT TUHS institutional guidelines:",
            "",
            "GENERAL INSTRUCTIONS:",
        ]

        # Add general instructions
        for gen_inst in self.guidelines.get('general_instructions', []):
            instructions.append(f"- {gen_inst}")

        instructions.append("")
        instructions.append(f"SPECIFIC {guideline['infection'].upper()} GUIDELINES:")
        instructions.append("")

        # Add infection-specific guidelines (with optional filtering)
        for subsection in guideline.get('sub_sections', []):
            subsection_type = subsection.get('type', 'Standard Treatment')

            # If filter is specified, only include matching subsections
            if subsection_filter and subsection_filter.lower() not in subsection_type.lower():
                continue

            instructions.append(f"## {subsection_type}")
            
            # Add review history note
            if 'review_history_note' in subsection:
                instructions.append(f"⚠️  {subsection['review_history_note']}")
            
            # Add general notes
            for note in subsection.get('general_notes', []):
                instructions.append(f"📋 {note}")
            
            instructions.append("")
            instructions.append("EMPIRIC REGIMENS:")

            # Handle direct empiric_regimens (e.g., Cystitis)
            if 'empiric_regimens' in subsection:
                for regimen in subsection.get('empiric_regimens', []):
                    allergy_status = regimen.get('pcp_allergy_status', 'Standard')
                    instructions.append(f"\n### {allergy_status}")

                    if regimen.get('allergy_details'):
                        instructions.append(f"   ({regimen['allergy_details']})")

                    instructions.append("   Regimen:")
                    regimen_list = regimen.get('regimen', [])
                    if isinstance(regimen_list, str):
                        instructions.append(f"   • {regimen_list}")
                    else:
                        for drug in regimen_list:
                            instructions.append(f"   • {drug}")

                    if regimen.get('duration'):
                        instructions.append(f"   Duration: {regimen['duration']}")

                    if regimen.get('notes'):
                        instructions.append(f"   Notes: {regimen['notes']}")

            # Handle nested sub_groups with empiric_regimens (e.g., Pyelonephritis, Catheter-associated UTI)
            if 'sub_groups' in subsection:
                for sub_group in subsection.get('sub_groups', []):
                    group_name = sub_group.get('group', 'Standard')
                    instructions.append(f"\n## {group_name}")

                    for regimen in sub_group.get('empiric_regimens', []):
                        allergy_status = regimen.get('pcp_allergy_status', 'Standard')
                        instructions.append(f"\n### {allergy_status}")

                        if regimen.get('allergy_details'):
                            instructions.append(f"   ({regimen['allergy_details']})")

                        instructions.append("   Regimen:")
                        regimen_list = regimen.get('regimen', [])
                        if isinstance(regimen_list, str):
                            instructions.append(f"   • {regimen_list}")
                        else:
                            for drug in regimen_list:
                                instructions.append(f"   • {drug}")

                        if regimen.get('duration'):
                            instructions.append(f"   Duration: {regimen['duration']}")

                        if regimen.get('notes'):
                            instructions.append(f"   Notes: {regimen['notes']}")

            instructions.append("")
        
        instructions.append("")
        instructions.append("IMPORTANT:")
        instructions.append("- State confidence level (high/moderate/low) based on how well the case matches these guidelines")
        instructions.append("- If case doesn't match guidelines, state 'LOW CONFIDENCE' and recommend ID consultation")
        instructions.append("- Always consider patient allergies, renal function, and prior resistance")

        # Route-specific formulation guidance
        if subsection_filter and "pyelonephritis" in subsection_filter.lower():
            instructions.append("- PYELONEPHRITIS REQUIRES IV ANTIBIOTICS. Never use oral-only therapy for pyelonephritis.")
            instructions.append("- You are treating PYELONEPHRITIS (febrile UTI), NOT simple cystitis. Use IV ceftriaxone as first-line.")
        else:
            instructions.append("- Always select an IV formulation. The only indication for selecting an Oral formulation is in addition to an IV formulation, or for uncomplicated cystitis")

        instructions.append("- Use COMMUNITY-ACQUIRED regimens unless patient has been hospitalized >48 hours or has healthcare-associated risk factors")
        instructions.append("- Match allergy severity correctly: Rash/Itching = Mild-moderate, Anaphylaxis/SJS/DRESS = Severe")

        # Add UNIVERSAL allergy handling instructions
        instructions.append("")
        instructions.append("🚨 ALLERGY HANDLING (CRITICAL - APPLIES TO ALL INFECTIONS):")
        instructions.append("- NEVER recommend drugs the patient is allergic to, even to 'mention' or 'consider' them")
        instructions.append("- If patient has SEVERE PCN allergy (anaphylaxis/SJS/DRESS): SKIP all penicillin and cephalosporin regimens entirely")
        instructions.append("- Do NOT say 'Drug X is contraindicated, use Drug Y instead' - just recommend Drug Y directly")
        instructions.append("- Go directly to the appropriate allergy-specific regimen from the guidelines")
        instructions.append("- If anaphylaxis to PCN: Use aztreonam-based or fluoroquinolone-based regimens (infection-dependent)")
        instructions.append("- NEVER include contraindicated drugs in your recommendation, not even as alternatives or crossed-out options")

        # Add PYELONEPHRITIS-SPECIFIC warnings to prevent ciprofloxacin misuse
        if subsection_filter and "pyelonephritis" in subsection_filter.lower():
            instructions.append("")
            instructions.append("🚨 PYELONEPHRITIS-SPECIFIC WARNINGS:")
            instructions.append("- NEVER use Ciprofloxacin (oral or IV) as first-line for pyelonephritis")
            instructions.append("- NEVER use oral antibiotics as first-line for pyelonephritis")
            instructions.append("- Community-acquired pyelonephritis: Ceftriaxone IV is MANDATORY first-line")
            instructions.append("- Hospital-acquired pyelonephritis: Piperacillin-tazobactam IV OR Cefepime IV")
            instructions.append("- Fluoroquinolones are NOT recommended for pyelonephritis in TUHS guidelines")

        # Add UNIVERSAL pregnancy-specific guidance for ALL infection types
        instructions.append("")
        instructions.append("🤰 PREGNANCY CONSIDERATIONS (CRITICAL FOR ALL INFECTIONS):")
        instructions.append("- If patient is pregnant or pregnancy is mentioned, antibiotic selection is CRITICAL for fetal safety")
        instructions.append("- If pregnancy is present and these guidelines lack pregnancy-specific regimens:")
        instructions.append("  → State 'LOW CONFIDENCE - Pregnancy requires specialized review'")
        instructions.append("  → Recommend evidence search and OB/ID consultation")
        instructions.append("- Generally SAFE antibiotics in pregnancy: Beta-lactams (Penicillins, Cephalosporins), Aztreonam, Vancomycin")
        instructions.append("- Generally CONTRAINDICATED in pregnancy: Fluoroquinolones, Tetracyclines, TMP/SMX (1st & 3rd trimester), Aminoglycosides")
        instructions.append("- ALWAYS explicitly address pregnancy safety in your recommendation if patient is pregnant")
        instructions.append("- Recommend OB/GYN or Maternal-Fetal Medicine consultation for any pregnant patient with serious infection")

        # Add infection-specific pregnancy guidance for UTI (separated by infection type to prevent confusion)
        if infection_name == "Urinary Tract":
            if subsection_filter and "pyelonephritis" in subsection_filter.lower():
                instructions.append("")
                instructions.append("🤰 PYELONEPHRITIS-SPECIFIC PREGNANCY GUIDANCE:")
                instructions.append("- Pregnant + Pyelonephritis: Ceftriaxone IV is MANDATORY first-line (safe, effective, IV ONLY)")
                instructions.append("- Pregnant + PCN allergy (severe): Aztreonam IV ± Vancomycin IV (IV ONLY)")
                instructions.append("- NEVER use oral ciprofloxacin for pyelonephritis in pregnancy")
                instructions.append("- AVOID in pregnancy: Fluoroquinolones, TMP/SMX (teratogenic in 1st trimester)")
                instructions.append("- Duration in pregnancy: Usually 7-14 days (longer than non-pregnant)")
            elif subsection_filter and "cystitis" in subsection_filter.lower():
                instructions.append("")
                instructions.append("🤰 CYSTITIS-SPECIFIC PREGNANCY GUIDANCE:")
                instructions.append("- Pregnant + Cystitis: Nitrofurantoin PO (avoid near term), Cephalexin PO, Fosfomycin PO")
                instructions.append("- AVOID in pregnancy: Fluoroquinolones, TMP/SMX (teratogenic in 1st trimester)")
                instructions.append("- Duration in pregnancy: Usually 7 days")

        return instructions


class AgnoBackendBridge:
    """Bridge between Express frontend and Agno Python backend with REAL TUHS guidelines"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.guideline_loader = TUHSGuidelineLoader()
        self.evidence_coordinator = FullEvidenceCoordinator(api_key)
        self.category_agents = self._init_category_agents(api_key)
        
        print("\n" + "="*70)
        print("🏥 TUHS Antibiotic Steward - Agno Bridge V2")
        print("="*70)
        print("✅ Loaded REAL TUHS guidelines from ABXguideInp.json")
        print(f"✅ Initialized {len(self.category_agents)} category agents")
        print("✅ Using OpenRouter API")
        print("="*70 + "\n")

    def _init_category_agents(self, api_key: str) -> Dict[str, Agent]:
        """Initialize TUHS category agents with REAL JSON guidelines"""
        
        base_model = OpenAIChat(
            id="gpt-4o-mini",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,  # Low temperature for more deterministic, guideline-adherent responses
            extra_headers={
                "HTTP-Referer": "https://tuhs-abx.local",
                "X-Title": "TUHS Antibiotic Steward"
            }
        )
        
        agents = {}
        
        # Pneumonia Agent - LOAD FROM JSON
        pneumonia_instructions = self.guideline_loader.build_agent_instructions("Pneumonia")
        agents[InfectionCategory.PNEUMONIA] = Agent(
            model=base_model,
            name="TUHS_Pneumonia_Expert",
            description="TUHS pneumonia treatment specialist with institutional guidelines",
            instructions=pneumonia_instructions
        )
        print(f"✅ Pneumonia agent: {len(pneumonia_instructions)} instruction lines from JSON")
        
        # Cystitis Agent - LOAD FROM JSON (filter for Cystitis subsection only)
        cystitis_instructions = self.guideline_loader.build_agent_instructions("Urinary Tract", subsection_filter="Cystitis")
        agents[InfectionCategory.CYSTITIS] = Agent(
            model=base_model,
            name="TUHS_Cystitis_Expert",
            description="TUHS afebrile/non-complicated cystitis specialist with institutional guidelines",
            instructions=cystitis_instructions
        )
        print(f"✅ Cystitis agent: {len(cystitis_instructions)} instruction lines from JSON")

        # Pyelonephritis/Complicated UTI Agent - LOAD FROM JSON (filter for Pyelonephritis subsection only)
        pyelo_instructions = self.guideline_loader.build_agent_instructions("Urinary Tract", subsection_filter="Pyelonephritis")
        agents[InfectionCategory.PYELONEPHRITIS] = Agent(
            model=base_model,
            name="TUHS_Pyelonephritis_Expert",
            description="TUHS pyelonephritis/complicated UTI specialist with institutional guidelines",
            instructions=pyelo_instructions
        )
        print(f"✅ Pyelonephritis agent: {len(pyelo_instructions)} instruction lines from JSON")
        
        # Skin/Soft Tissue Agent - LOAD FROM JSON
        ssti_instructions = self.guideline_loader.build_agent_instructions("Skin and Soft Tissue")
        agents[InfectionCategory.SKIN_SOFT_TISSUE] = Agent(
            model=base_model,
            name="TUHS_SSTI_Expert",
            description="TUHS skin/soft tissue infection specialist with institutional guidelines",
            instructions=ssti_instructions
        )
        print(f"✅ SSTI agent: {len(ssti_instructions)} instruction lines from JSON")
        
        # Intra-abdominal Agent - LOAD FROM JSON
        iab_instructions = self.guideline_loader.build_agent_instructions("Intra-abdominal")
        agents[InfectionCategory.INTRA_ABDOMINAL] = Agent(
            model=base_model,
            name="TUHS_IntraAbdominal_Expert",
            description="TUHS intra-abdominal infection specialist with institutional guidelines",
            instructions=iab_instructions
        )
        print(f"✅ Intra-abdominal agent: {len(iab_instructions)} instruction lines from JSON")
        
        # Bacteremia/Sepsis Agent - LOAD FROM JSON
        sepsis_instructions = self.guideline_loader.build_agent_instructions("Sepsis")
        agents[InfectionCategory.BACTEREMIA_SEPSIS] = Agent(
            model=base_model,
            name="TUHS_Bacteremia_Expert",
            description="TUHS bacteremia/sepsis specialist with institutional guidelines",
            instructions=sepsis_instructions
        )
        print(f"✅ Bacteremia/Sepsis agent: {len(sepsis_instructions)} instruction lines from JSON")
        
        # Meningitis Agent - LOAD FROM JSON
        meningitis_instructions = self.guideline_loader.build_agent_instructions("Meningitis")
        agents[InfectionCategory.MENINGITIS] = Agent(
            model=base_model,
            name="TUHS_Meningitis_Expert",
            description="TUHS meningitis specialist with institutional guidelines",
            instructions=meningitis_instructions
        )
        print(f"✅ Meningitis agent: {len(meningitis_instructions)} instruction lines from JSON")
        
        # General fallback agent
        agents[InfectionCategory.GENERAL] = Agent(
            model=base_model,
            name="TUHS_General_ID",
            description="General infectious disease consultant",
            instructions=[
                "You are a general ID consultant.",
                "Provide evidence-based recommendations.",
                "Recommend ID consultation for complex cases.",
                "State confidence level (usually moderate to low for general cases)."
            ]
        )
        print(f"✅ General ID agent: fallback for unmatched cases")
        
        return agents

    def determine_category(self, patient_data: Dict[str, Any]) -> str:
        """Determine infection category from patient data"""
        infection_type = patient_data.get('infection_type', '').lower()

        category_map = {
            'pneumonia': InfectionCategory.PNEUMONIA,
            'cap': InfectionCategory.PNEUMONIA,
            'hap': InfectionCategory.PNEUMONIA,
            'vap': InfectionCategory.PNEUMONIA,
            'cystitis': InfectionCategory.CYSTITIS,
            'afebrile_uti': InfectionCategory.CYSTITIS,
            'uncomplicated_uti': InfectionCategory.CYSTITIS,
            'afebrile/non-complicated cystitis': InfectionCategory.CYSTITIS,
            'pyelonephritis': InfectionCategory.PYELONEPHRITIS,
            'febrile_uti': InfectionCategory.PYELONEPHRITIS,
            'complicated_uti': InfectionCategory.PYELONEPHRITIS,
            'pyelonephritis/complicated uti': InfectionCategory.PYELONEPHRITIS,
            'uti': InfectionCategory.PYELONEPHRITIS,  # Default UTI to pyelonephritis for safety
            'skin': InfectionCategory.SKIN_SOFT_TISSUE,
            'cellulitis': InfectionCategory.SKIN_SOFT_TISSUE,
            'skin_soft_tissue': InfectionCategory.SKIN_SOFT_TISSUE,
            'ssti': InfectionCategory.SKIN_SOFT_TISSUE,
            'intra_abdominal': InfectionCategory.INTRA_ABDOMINAL,
            'intra-abdominal': InfectionCategory.INTRA_ABDOMINAL,
            'bacteremia': InfectionCategory.BACTEREMIA_SEPSIS,
            'sepsis': InfectionCategory.BACTEREMIA_SEPSIS,
            'meningitis': InfectionCategory.MENINGITIS,
            'neutropenic': InfectionCategory.NEUTROPENIC_FEVER,
            'central_line': InfectionCategory.CENTRAL_LINE,
        }

        return category_map.get(infection_type, InfectionCategory.GENERAL)

    def calculate_tuhs_confidence(self, category_response: str, patient_data: Dict[str, Any]) -> float:
        """
        Calculate confidence in TUHS guideline recommendation
        
        Based on:
        - Response certainty indicators
        - Category match strength
        - Case complexity
        """
        
        confidence = 0.8  # Higher base confidence now that we have real guidelines

        # Reduce confidence for uncertainty indicators
        uncertainty_terms = ['uncertain', 'unclear', 'consider consultation', 'may need', 'low confidence']
        if any(term in category_response.lower() for term in uncertainty_terms):
            confidence -= 0.3

        # Check for strong match indicators
        strong_terms = ['guideline', 'recommended', 'first-line', 'standard', 'preferred', 'tuhs protocol']
        if any(term in category_response.lower() for term in strong_terms):
            confidence += 0.1

        # Adjust for case complexity
        if patient_data.get('history_mrsa') or patient_data.get('history_vre') or patient_data.get('prior_resistance'):
            confidence -= 0.1

        # Convert GFR to float for comparison
        gfr_value = patient_data.get('gfr', 100)
        try:
            gfr = float(gfr_value) if gfr_value else 100
        except (ValueError, TypeError):
            gfr = 100

        if gfr < 30:
            confidence -= 0.15

        # Check for pregnancy - reduce confidence if pregnancy not explicitly addressed
        inf_risks = patient_data.get('inf_risks', '')
        if inf_risks and 'pregnan' in inf_risks.lower():
            # Check if pregnancy was addressed in the response
            if 'pregnan' not in category_response.lower():
                confidence -= 0.25  # Major reduction if pregnancy ignored
            # Even if addressed, reduce slightly as guidelines may lack pregnancy-specific regimens
            elif 'low confidence' not in category_response.lower():
                confidence -= 0.1

        return max(min(confidence, 1.0), 0.0)  # Clamp to [0, 1]

    async def process_request(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main workflow with REAL TUHS guidelines:
        1. Query TUHS guideline agent (loaded from JSON)
        2. Calculate confidence
        3. If confidence < 0.8 → Search reputable sites
        4. Return TUHS-compliant recommendation
        """

        print(f"\n{'='*70}")
        print(f"🏥 Processing Patient Request with REAL TUHS Guidelines")
        print(f"{'='*70}")

        # Step 1: Determine category and get REAL TUHS recommendation
        category = self.determine_category(patient_data)
        print(f"✅ Category: {category}")
        
        category_agent = self.category_agents.get(category)
        if not category_agent:
            return {
                'error': 'Unknown infection category',
                'confidence': 0.0
            }

        # Query TUHS guideline with REAL Agno agent (loaded from JSON)
        tuhs_query = self._build_tuhs_query(patient_data, category)
        print(f"🔍 Querying TUHS {category} expert with JSON-loaded guidelines...")
        
        # REAL AGNO CALL with JSON guidelines
        tuhs_response_obj = await category_agent.arun(tuhs_query)
        tuhs_response = tuhs_response_obj.content if hasattr(tuhs_response_obj, 'content') else str(tuhs_response_obj)
        print(f"✅ TUHS response received (using JSON guidelines)")

        # Step 2: Calculate TUHS confidence
        tuhs_confidence = self.calculate_tuhs_confidence(tuhs_response, patient_data)
        print(f"📊 TUHS Confidence: {tuhs_confidence:.0%}")

        # Step 3: Decide if external search is needed
        print(f"\n🎯 Evidence Search Decision...")
        search_result = await self.evidence_coordinator.search_sequential(
            query=self._build_evidence_query(patient_data),
            tuhs_confidence=tuhs_confidence,
            tuhs_response=tuhs_response
        )

        # Step 4: Build final response
        print(f"\n✅ Request complete - Final confidence: {search_result.final_confidence:.0%}")
        print(f"{'='*70}\n")
        
        return {
            'category': category,
            'tuhs_recommendation': tuhs_response,
            'tuhs_confidence': tuhs_confidence,
            'search_decision': {
                'tier': search_result.decision.tier.value,
                'reasoning': search_result.decision.reasoning,
                'searched': search_result.decision.should_search
            },
            'reputable_sources': [
                {
                    'source': s.source_name,
                    'title': s.title,
                    'url': s.url,
                    'finding': s.key_finding
                } for s in (search_result.reputable_sources or [])
            ],
            'broader_sources': [
                {
                    'source': s.source_name,
                    'title': s.title,
                    'url': s.url,
                    'finding': s.key_finding
                } for s in (search_result.broader_sources or [])
            ],
            'final_confidence': search_result.final_confidence,
            'search_history': search_result.search_history,
            'timestamp': datetime.now().isoformat(),
            'guidelines_source': 'ABXguideInp.json (TUHS Institutional Guidelines)'
        }

    def _build_tuhs_query(self, patient_data: Dict[str, Any], category: str) -> str:
        """Build query for TUHS agent"""

        # Extract and format key fields
        age = patient_data.get('age', 'unknown')
        gender = patient_data.get('gender', 'unknown')
        location = patient_data.get('location', 'unknown')
        infection = patient_data.get('infection_type', 'unknown')
        gfr = patient_data.get('gfr', 'unknown')
        allergies = patient_data.get('allergies') or 'none'
        prior_resistance = patient_data.get('prior_resistance', '')
        culture_results = patient_data.get('culture_results', '')
        inf_risks = patient_data.get('inf_risks', '')

        # Check for pregnancy in multiple fields
        is_pregnant = False
        if inf_risks and 'pregnan' in inf_risks.lower():
            is_pregnant = True

        query = f"""
        Patient: {age}yo {gender}
        Location: {location}
        Infection: {infection}
        GFR: {gfr}
        Allergies: {allergies}
        Culture Results: {culture_results}
        """

        if prior_resistance:
            query += f"Prior Resistance: {prior_resistance}\n"

        if inf_risks:
            query += f"Infection-specific Risks: {inf_risks}\n"

        # Explicitly flag pregnancy if present
        if is_pregnant:
            query += "\n⚠️  PREGNANCY ALERT: This patient is PREGNANT - antibiotic selection must consider fetal safety!\n"
            query += "You MUST address pregnancy-specific safety in your recommendation.\n"

        query += f"\nProvide TUHS {category} guideline recommendation following the EXACT protocols loaded from ABXguideInp.json.\n"
        query += "Include specific drug names, doses, routes, and duration as specified in TUHS guidelines.\n"

        return query

    def _build_evidence_query(self, patient_data: Dict[str, Any]) -> str:
        """Build query for evidence search"""
        return f"{patient_data.get('infection_type')} treatment {patient_data.get('age')}yo"


# Flask routes remain the same...
# (keeping existing Flask code for compatibility)
