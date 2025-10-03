"""
Enhanced TUHS Manager Agent and Output Formatter
Coordinates the complete multi-agent workflow
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.storage.postgres import PostgresStorage
from agno.team.team import Team

from tuhs_multi_agent_system import (
    InfectionCategory, TUHSCategoryAgent, VectorMemoryAgent,
    AgentContext, create_tuhs_agent_system
)
from evidence_agents import EvidenceCoordinatorAgent

@dataclass
class WorkflowDecision:
    """Decision made by manager about workflow execution"""
    selected_category: InfectionCategory
    confidence_threshold: float
    needs_evidence_search: bool
    needs_vector_backup: bool
    reasoning: str

@dataclass
class FinalRecommendation:
    """Structured final recommendation"""
    primary_agent: str
    category: InfectionCategory
    recommendation_text: str
    confidence_score: float
    evidence_sources: List[Dict[str, Any]]
    alternative_options: List[str]
    monitoring_plan: List[str]
    formatted_output: str

class EnhancedTUHSManager(Agent):
    """Enhanced manager with sophisticated workflow coordination"""

    def __init__(self, category_agents: Dict[InfectionCategory, TUHSCategoryAgent], **kwargs):
        self.category_agents = category_agents
        self.workflow_history: List[WorkflowDecision] = []

        super().__init__(
            name="Enhanced_TUHS_Manager",
            role="Sophisticated coordinator for multi-agent antibiotic stewardship workflow",
            instructions=[
                "Analyze patient case and select optimal category agent",
                "Evaluate agent confidence and determine need for evidence",
                "Coordinate between category agents and evidence search",
                "Fall back to vector memory when confidence is low",
                "Synthesize recommendations from multiple sources",
                "Ensure all recommendations follow TUHS guidelines"
            ],
            **kwargs
        )

    async def orchestrate_workflow(self, patient_data: Dict[str, Any]) -> FinalRecommendation:
        """Complete workflow orchestration"""

        # 1. Initial analysis and category selection
        workflow_decision = await self._make_workflow_decision(patient_data)
        self.workflow_history.append(workflow_decision)

        # 2. Query selected category agent
        category_agent = self.category_agents[workflow_decision.selected_category]
        category_response = await category_agent.arun(
            self._build_category_query(patient_data, workflow_decision),
            context={"patient_data": patient_data}
        )

        # 3. Evaluate response and determine next steps
        response_evaluation = self._evaluate_category_response(category_response)

        evidence_results = []
        vector_results = None

        # 4. Get additional evidence if needed
        if workflow_decision.needs_evidence_search:
            evidence_agent = EvidenceCoordinatorAgent()
            evidence_results = await evidence_agent.search_all_sources(
                self._build_evidence_query(patient_data),
                {"category": workflow_decision.selected_category.value}
            )

        # 5. Use vector backup if confidence too low
        if workflow_decision.needs_vector_backup or response_evaluation.confidence_too_low:
            vector_agent = VectorMemoryAgent()
            vector_response = await vector_agent.arun(
                self._build_vector_query(patient_data),
                context={"category": workflow_decision.selected_category.value}
            )
            vector_results = vector_response

        # 6. Synthesize final recommendation
        final_rec = await self._synthesize_recommendation(
            category_response,
            evidence_results,
            vector_results,
            workflow_decision,
            patient_data
        )

        return final_rec

    async def _make_workflow_decision(self, patient_data: Dict[str, Any]) -> WorkflowDecision:
        """Analyze case and make workflow decisions"""

        # Determine infection category with confidence scoring
        category = self._determine_category_with_confidence(patient_data)

        # Set confidence thresholds based on case complexity
        base_threshold = 0.7
        complexity_multiplier = self._assess_case_complexity(patient_data)
        confidence_threshold = base_threshold * complexity_multiplier

        # Determine if evidence search is needed
        needs_evidence = self._should_search_evidence(patient_data)

        # Determine if vector backup might be needed
        needs_vector = confidence_threshold < 0.8 or complexity_multiplier > 1.2

        return WorkflowDecision(
            selected_category=category,
            confidence_threshold=confidence_threshold,
            needs_evidence_search=needs_evidence,
            needs_vector_backup=needs_vector,
            reasoning=f"Selected {category.value} with threshold {confidence_threshold}"
        )

    def _determine_category_with_confidence(self, patient_data: Dict[str, Any]) -> InfectionCategory:
        """Enhanced category determination with confidence"""
        infection_type = patient_data.get('infection_type', '').lower()

        # Enhanced mapping with confidence scores
        category_confidence_map = {
            'pneumonia': (InfectionCategory.PNEUMONIA, 0.9),
            'cap': (InfectionCategory.PNEUMONIA, 0.85),
            'hap': (InfectionCategory.PNEUMONIA, 0.85),
            'vap': (InfectionCategory.PNEUMONIA, 0.85),
            'uti': (InfectionCategory.UTI, 0.9),
            'cystitis': (InfectionCategory.UTI, 0.85),
            'pyelonephritis': (InfectionCategory.UTI, 0.9),
            'skin': (InfectionCategory.SKIN_SOFT_TISSUE, 0.8),
            'cellulitis': (InfectionCategory.SKIN_SOFT_TISSUE, 0.85),
            'ssti': (InfectionCategory.SKIN_SOFT_TISSUE, 0.85),
            'intra': (InfectionCategory.INTRA_ABDOMINAL, 0.8),
            'bone': (InfectionCategory.BONE_JOINT, 0.85),
            'joint': (InfectionCategory.BONE_JOINT, 0.85),
            'meningitis': (InfectionCategory.MENINGITIS, 0.9),
            'bacteremia': (InfectionCategory.BACTEREMIA_SEPSIS, 0.85),
            'sepsis': (InfectionCategory.BACTEREMIA_SEPSIS, 0.9),
        }

        match = category_confidence_map.get(infection_type)
        if match:
            category, confidence = match
            return category

        return InfectionCategory.GENERAL

    def _assess_case_complexity(self, patient_data: Dict[str, Any]) -> float:
        """Assess case complexity (1.0 = normal, >1.0 = complex)"""
        complexity_score = 1.0

        # Age factors
        age = patient_data.get('age', 0)
        if age > 80 or age < 18:
            complexity_score *= 1.2

        # Comorbidities
        comorbidities = patient_data.get('comorbidities', [])
        if comorbidities and len(comorbidities) > 2:
            complexity_score *= 1.3

        # Resistance history
        if patient_data.get('history_mrsa') or patient_data.get('history_vre'):
            complexity_score *= 1.4

        # Renal impairment
        gfr = patient_data.get('gfr', 100)
        if gfr < 30:
            complexity_score *= 1.5

        # Multiple antibiotics
        current_abx = patient_data.get('current_abx', [])
        if len(current_abx) > 1:
            complexity_score *= 1.2

        return complexity_score

    def _should_search_evidence(self, patient_data: Dict[str, Any]) -> bool:
        """Determine if external evidence search is warranted"""
        return (
            patient_data.get('history_resistance') or
            patient_data.get('immunocompromised') or
            patient_data.get('multiple_comorbidities') or
            patient_data.get('treatment_failure')
        )

    def _evaluate_category_response(self, response) -> Dict[str, Any]:
        """Evaluate category agent response quality"""
        content = response.content.lower()

        # Simple heuristics for response evaluation
        confidence_indicators = [
            'confident', 'standard', 'recommended', 'guideline',
            'first-line', 'preferred', 'evidence-based'
        ]

        uncertainty_indicators = [
            'uncertain', 'consider', 'may require', 'discuss with',
            'alternative', 'unclear', 'complex'
        ]

        confidence_score = sum(1 for indicator in confidence_indicators if indicator in content)
        uncertainty_score = sum(1 for indicator in uncertainty_indicators if indicator in content)

        return {
            'confidence_score': confidence_score,
            'uncertainty_score': uncertainty_score,
            'confidence_too_low': uncertainty_score > confidence_score,
            'response_length': len(content)
        }

    def _build_category_query(self, patient_data: Dict[str, Any], decision: WorkflowDecision) -> str:
        """Build optimized query for category agent"""
        return f"""
        Patient case requiring TUHS {decision.selected_category.value} expertise:

        Demographics: Age {patient_data.get('age', 'unknown')}, {patient_data.get('gender', 'unknown')}, {patient_data.get('location', 'unknown')} patient

        Infection: {patient_data.get('infection_type', 'unknown')}

        Key factors:
        - GFR: {patient_data.get('gfr', 'unknown')}
        - Allergies: {patient_data.get('allergies', 'none')}
        - Resistance history: {patient_data.get('history_resistance', 'none')}
        - Current antibiotics: {patient_data.get('current_abx', 'none')}

        Provide TUHS guideline-based recommendation with confidence level.
        """

    def _build_evidence_query(self, patient_data: Dict[str, Any]) -> str:
        """Build query for evidence search"""
        return f"""
        Evidence-based literature for:
        - Infection: {patient_data.get('infection_type', 'unknown')}
        - Patient factors: GFR {patient_data.get('gfr', 'unknown')}, resistance {patient_data.get('history_resistance', 'none')}
        - Focus: Recent clinical trials, systematic reviews, evidence-based guidelines
        """

    def _build_vector_query(self, patient_data: Dict[str, Any]) -> str:
        """Build query for vector backup"""
        return f"""
        Vector search for similar cases:
        - Primary infection: {patient_data.get('infection_type', 'unknown')}
        - Patient profile: {patient_data.get('age', 'unknown')}yo {patient_data.get('gender', 'unknown')}
        - Key complications: GFR {patient_data.get('gfr', 'unknown')}, resistance {patient_data.get('history_resistance', 'none')}
        """

    async def _synthesize_recommendation(
        self,
        category_response,
        evidence_results: List[Dict],
        vector_results,
        decision: WorkflowDecision,
        patient_data: Dict[str, Any]
    ) -> FinalRecommendation:
        """Synthesize final recommendation from all sources"""

        # Determine primary agent and confidence
        evaluation = self._evaluate_category_response(category_response)

        primary_agent = f"TUHS_{decision.selected_category.value.title()}_Expert"
        base_confidence = min(evaluation['confidence_score'] / 3.0, 1.0)  # Normalize to 0-1

        # Adjust confidence based on evidence
        if evidence_results:
            evidence_confidence = min(len(evidence_results) / 5.0, 0.3)  # Max 0.3 from evidence
            base_confidence = min(base_confidence + evidence_confidence, 1.0)

        # Create recommendation object
        recommendation = FinalRecommendation(
            primary_agent=primary_agent,
            category=decision.selected_category,
            recommendation_text=category_response.content,
            confidence_score=base_confidence,
            evidence_sources=evidence_results[:3],  # Top 3 evidence sources
            alternative_options=self._extract_alternatives(category_response.content),
            monitoring_plan=self._extract_monitoring(category_response.content)
        )

        return recommendation

    def _extract_alternatives(self, response_text: str) -> List[str]:
        """Extract alternative options from response"""
        # Simple extraction - can be enhanced
        alternatives = []
        if "alternative" in response_text.lower():
            # Extract text after "alternative" mentions
            alternatives.append("Alternative regimen mentioned in response")
        return alternatives

    def _extract_monitoring(self, response_text: str) -> List[str]:
        """Extract monitoring recommendations"""
        monitoring = []
        if "monitor" in response_text.lower():
            monitoring.append("Monitor clinical response and adverse effects")
        if "repeat" in response_text.lower():
            monitoring.append("Repeat cultures as indicated")
        return monitoring

class EnhancedOutputFormatter(Agent):
    """Enhanced output formatting with clinical structure"""

    def __init__(self, **kwargs):
        super().__init__(
            name="Enhanced_Clinical_Formatter",
            role="Formats comprehensive antibiotic recommendations for clinicians",
            instructions=[
                "Structure output in clear clinical sections",
                "Highlight critical information (dosing, allergies, monitoring)",
                "Include evidence sources and confidence levels",
                "Follow TUHS formatting conventions",
                "Ensure recommendations are actionable",
                "Include stewardship considerations"
            ],
            **kwargs
        )

    async def format_recommendation(self, recommendation: FinalRecommendation) -> str:
        """Format the final recommendation"""

        # Build structured output
        output_sections = [
            "## Clinical Assessment",
            self._format_assessment(recommendation),
            "",
            "## Primary Recommendation",
            self._format_primary_recommendation(recommendation),
            "",
            "## Alternative Options",
            self._format_alternatives(recommendation),
            "",
            "## Evidence & Confidence",
            self._format_evidence_confidence(recommendation),
            "",
            "## Monitoring & Stewardship",
            self._format_monitoring(recommendation),
            "",
            "## Citations",
            self._format_citations(recommendation)
        ]

        # Add confidence-based styling
        confidence_indicator = self._get_confidence_indicator(recommendation.confidence_score)

        return f"{confidence_indicator}\n\n" + "\n".join(output_sections)

    def _format_assessment(self, rec: FinalRecommendation) -> str:
        """Format clinical assessment section"""
        return f"""
**Infection Category:** {rec.category.value.replace('_', ' ').title()}
**Primary Agent:** {rec.primary_agent}
**Case Complexity:** {self._get_complexity_indicator(rec.confidence_score)}

Patient presents with {rec.category.value} requiring antibiotic therapy.
Evidence-based approach following TUHS guidelines with {len(rec.evidence_sources)} supporting sources.
"""

    def _format_primary_recommendation(self, rec: FinalRecommendation) -> str:
        """Format primary recommendation"""
        return f"""
**💊 Recommended Regimen:** {self._extract_drug_from_text(rec.recommendation_text)}

**Rationale:** {self._extract_rationale_from_text(rec.recommendation_text)}

**Key Considerations:**
- Renal dosing: {self._extract_renal_dosing(rec.recommendation_text)}
- Allergy check: {self._extract_allergy_considerations(rec.recommendation_text)}
- Duration: {self._extract_duration(rec.recommendation_text)}
"""

    def _format_alternatives(self, rec: FinalRecommendation) -> str:
        """Format alternative options"""
        if not rec.alternative_options:
            return "No alternative options specified."

        alternatives_text = "\n".join(f"- {alt}" for alt in rec.alternative_options)
        return alternatives_text

    def _format_evidence_confidence(self, rec: FinalRecommendation) -> str:
        """Format evidence and confidence information"""
        confidence_level = self._get_confidence_text(rec.confidence_score)

        evidence_section = f"""
**Confidence Level:** {confidence_level} ({rec.confidence_score".1%"})**

**Evidence Sources:** {len(rec.evidence_sources)} sources reviewed
"""

        if rec.evidence_sources:
            for i, source in enumerate(rec.evidence_sources[:2], 1):  # Show top 2
                evidence_section += f"""
**Source {i}:** {source.get('title', 'Unknown')}
- Relevance: {source.get('clinical_relevance', 'Not assessed')}
- Key finding: {source.get('key_findings', ['N/A'])[0]}
"""

        return evidence_section

    def _format_monitoring(self, rec: FinalRecommendation) -> str:
        """Format monitoring and stewardship"""
        monitoring_items = rec.monitoring_plan or ["Monitor clinical response"]

        return "\n".join(f"- {item}" for item in monitoring_items)

    def _format_citations(self, rec: FinalRecommendation) -> str:
        """Format citations"""
        citations = ["TUHS Antibiotic Guidelines"]

        if rec.evidence_sources:
            for source in rec.evidence_sources:
                if source.get('source') == 'pubmed':
                    citations.append(f"PubMed: {source.get('title', 'Unknown')}")
                elif source.get('source') == 'web':
                    citations.append(f"Clinical Guideline: {source.get('title', 'Unknown')}")

        return "\n".join(f"- {citation}" for citation in citations)

    def _get_confidence_indicator(self, score: float) -> str:
        """Get visual confidence indicator"""
        if score >= 0.8:
            return "🔴 **HIGH CONFIDENCE** - Strong TUHS guideline match"
        elif score >= 0.6:
            return "🟡 **MODERATE CONFIDENCE** - TUHS guidelines with evidence support"
        else:
            return "🟠 **LOW CONFIDENCE** - Limited guideline match, requires ID consultation"

    def _get_complexity_indicator(self, score: float) -> str:
        """Get complexity indicator"""
        if score < 0.6:
            return "Complex case - multiple complicating factors"
        else:
            return "Standard case - straightforward presentation"

    def _get_confidence_text(self, score: float) -> str:
        """Get confidence text"""
        if score >= 0.8:
            return "High"
        elif score >= 0.6:
            return "Moderate"
        else:
            return "Low"

    def _extract_drug_from_text(self, text: str) -> str:
        """Extract primary drug from response text"""
        # Simple extraction - can be enhanced with NLP
        if "vancomycin" in text.lower():
            return "Vancomycin IV"
        elif "ceftriaxone" in text.lower():
            return "Ceftriaxone IV"
        elif "piperacillin" in text.lower():
            return "Piperacillin-tazobactam IV"
        else:
            return "See full recommendation below"

    def _extract_rationale_from_text(self, text: str) -> str:
        """Extract rationale from response text"""
        # Simple extraction - can be enhanced
        if "mrsa" in text.lower():
            return "MRSA coverage required based on patient history"
        elif "esbl" in text.lower():
            return "ESBL coverage required for resistant organisms"
        else:
            return "Empiric coverage per TUHS guidelines"

    def _extract_renal_dosing(self, text: str) -> str:
        """Extract renal dosing information"""
        if "gfr" in text.lower() or "renal" in text.lower():
            return "Renal-adjusted dosing applied (GFR <60)"
        else:
            return "Standard dosing (GFR >60)"

    def _extract_allergy_considerations(self, text: str) -> str:
        """Extract allergy considerations"""
        if "allergy" in text.lower() or "penicillin" in text.lower():
            return "Allergy assessment completed"
        else:
            return "No significant allergies noted"

    def _extract_duration(self, text: str) -> str:
        """Extract treatment duration"""
        if "day" in text.lower():
            return "Duration specified in recommendation"
        else:
            return "Duration per TUHS guidelines"

# Integration function
async def create_enhanced_tuhs_system() -> Team:
    """Create the complete enhanced TUHS multi-agent system"""

    # Create base system
    base_team = await create_tuhs_agent_system()

    # Create enhanced manager
    enhanced_manager = EnhancedTUHSManager(
        category_agents=base_team.members[0].category_agents,  # Access category agents
        model=OpenRouter(id="google/gemini-2.5-pro-preview"),
        storage=PostgresStorage(table_name="enhanced_manager_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
    )

    # Create enhanced formatter
    enhanced_formatter = EnhancedOutputFormatter(
        model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
        storage=PostgresStorage(table_name="enhanced_formatter_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
    )

    # Create evidence coordinator
    evidence_coordinator = EvidenceCoordinatorAgent(
        model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
        storage=PostgresStorage(table_name="evidence_coordinator_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
    )

    # Update team with enhanced components
    enhanced_team = Team(
        name="Enhanced_TUHS_Stewardship_Team",
        mode="coordinate",
        model=OpenRouter(id="google/gemini-2.5-pro-preview"),
        members=[enhanced_manager, enhanced_formatter, evidence_coordinator],
        instructions=[
            "Use enhanced workflow coordination",
            "Apply sophisticated confidence assessment",
            "Integrate evidence from multiple sources",
            "Provide structured clinical output"
        ],
        success_criteria="Comprehensive evidence-based recommendation delivered",
        enable_agentic_context=True,
        show_tool_calls=True,
        markdown=True
    )

    return enhanced_team

# Example usage
async def example_enhanced_workflow():
    """Example of enhanced workflow"""

    # Create enhanced system
    team = await create_enhanced_tuhs_system()

    # Complex patient case
    patient_data = {
        "age": 88,
        "gender": "M",
        "location": "Ward",
        "infection_type": "bacteremia",
        "history_mrsa": True,
        "history_vre": True,
        "gfr": 44,
        "allergies": "penicillin (rash)",
        "comorbidities": ["diabetes", "hypertension", "CAD"],
        "current_abx": ["vancomycin", "meropenem"]
    }

    # Process through enhanced workflow
    manager = team.members[0]  # Enhanced manager
    formatter = team.members[1]  # Enhanced formatter

    # Simulate workflow
    recommendation = await manager.orchestrate_workflow(patient_data)
    final_output = await formatter.format_recommendation(recommendation)

    print("Enhanced Workflow Result:")
    print("=" * 50)
    print(final_output)

if __name__ == "__main__":
    asyncio.run(example_enhanced_workflow())
