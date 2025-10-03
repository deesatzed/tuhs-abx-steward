"""
TUHS Multi-Agent Antibiotic Stewardship System
Advanced Agno Agent Architecture with Category-Specific Agents
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Agno imports
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.team.team import Team
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.pgvector import PgVector, SearchType
from agno.storage.postgres import PostgresStorage
from agno.tools.pubmed import PubmedTools
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.knowledge import KnowledgeTools
from agno.embedder.openai import OpenAIEmbedder

# Custom tools
from lib.clinicalTools import clinicalTools

# Database configuration
DB_URL = "postgresql://localhost:5432/tuhs_abx"
VECTOR_DB_URL = f"{DB_URL}_vector"

class InfectionCategory(str, Enum):
    PNEUMONIA = "pneumonia"
    UTI = "uti"
    SKIN_SOFT_TISSUE = "skin_soft_tissue"
    INTRA_ABDOMINAL = "intra_abdominal"
    BONE_JOINT = "bone_joint"
    MENINGITIS = "meningitis"
    BACTEREMIA_SEPSIS = "bacteremia_sepsis"
    NEUTROPENIC_FEVER = "neutropenic_fever"
    GENERAL = "general"

@dataclass
class AgentContext:
    """Context shared between agents"""
    patient_data: Dict[str, Any]
    infection_category: Optional[InfectionCategory] = None
    confidence_scores: Dict[str, float] = None
    evidence_found: List[Dict] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.confidence_scores is None:
            self.confidence_scores = {}
        if self.evidence_found is None:
            self.evidence_found = []
        if self.recommendations is None:
            self.recommendations = []

class TUHSCategoryAgent(Agent):
    """Specialized agent for specific TUHS guideline categories"""

    def __init__(self, category: InfectionCategory, **kwargs):
        self.category = category
        super().__init__(
            name=f"TUHS_{category.value.title()}_Expert",
            role=f"TUHS {category.value.replace('_', ' ').title()} guideline specialist",
            **kwargs
        )
        self.category_knowledge = self._load_category_knowledge()

    def _load_category_knowledge(self) -> Dict[str, Any]:
        """Load category-specific knowledge into agent context"""
        # This would load the relevant sections from TUHS guidelines
        # For now, return category metadata
        return {
            "category": self.category.value,
            "guidelines_path": f"/guidelines/tuhs/{self.category.value}",
            "common_regimens": self._get_common_regimens(),
            "key_considerations": self._get_key_considerations()
        }

    def _get_common_regimens(self) -> List[str]:
        """Get common regimens for this category"""
        regimens = {
            InfectionCategory.PNEUMONIA: [
                "Ceftriaxone + Azithromycin",
                "Piperacillin-tazobactam + Vancomycin",
                "Levofloxacin + Aztreonam"
            ],
            InfectionCategory.UTI: [
                "Ceftriaxone",
                "Piperacillin-tazobactam + Vancomycin",
                "Nitrofurantoin"
            ],
            InfectionCategory.SKIN_SOFT_TISSUE: [
                "Cefazolin",
                "Vancomycin",
                "Piperacillin-tazobactam + Vancomycin"
            ]
        }
        return regimens.get(self.category, [])

    def _get_key_considerations(self) -> List[str]:
        """Get key considerations for this category"""
        considerations = {
            InfectionCategory.PNEUMONIA: [
                "MRSA risk factors",
                "Pseudomonas risk factors",
                "Aspiration risk"
            ],
            InfectionCategory.UTI: [
                "Catheter-associated",
                "Upper vs lower tract",
                "Recent antibiotics"
            ]
        }
        return considerations.get(self.category, [])

class VectorMemoryAgent(Agent):
    """Backup agent using vector memory for uncertain cases"""

    def __init__(self, **kwargs):
        super().__init__(
            name="Vector_Memory_Backup",
            role="Provides vector-based guideline search when category agents are uncertain",
            **kwargs
        )

class EvidenceSearchAgent(Agent):
    """Agent for searching external evidence-based sources"""

    def __init__(self, **kwargs):
        super().__init__(
            name="Evidence_Search_Specialist",
            role="Searches PubMed, ArXiv, and web sources for evidence-based literature",
            tools=[
                PubmedTools(),
                ArxivTools(),
                DuckDuckGoTools()
            ],
            **kwargs
        )

class TUHSManagerAgent(Agent):
    """Main coordinator agent that manages the workflow"""

    def __init__(self, category_agents: Dict[InfectionCategory, TUHSCategoryAgent], **kwargs):
        self.category_agents = category_agents
        self.vector_agent = None
        self.evidence_agent = None
        self.output_formatter = None

        super().__init__(
            name="TUHS_Antibiotic_Manager",
            role="Coordinates TUHS guideline agents and evidence search for optimal recommendations",
            **kwargs
        )

    async def process_request(self, patient_data: Dict[str, Any]) -> Any:
        """Main workflow coordinator"""
        context = AgentContext(patient_data=patient_data)

        # 1. Determine infection category
        category = self._determine_category(patient_data)
        context.infection_category = category

        # 2. Query category-specific agent first
        category_agent = self.category_agents[category]
        category_response = await category_agent.arun(
            f"Patient data: {json.dumps(patient_data)}. Provide recommendation based on TUHS guidelines.",
            context={"category_context": category_agent.category_knowledge}
        )

        # 3. Check confidence and get additional evidence if needed
        if self._needs_evidence(category_response):
            evidence_response = await self.evidence_agent.arun(
                f"Find evidence-based literature for: {patient_data.get('infection_type', 'unknown infection')}",
                context={"patient_context": patient_data}
            )
            context.evidence_found = self._parse_evidence(evidence_response)

        # 4. Use vector backup if confidence is low
        if self._confidence_too_low(category_response):
            vector_response = await self.vector_agent.arun(
                f"Vector search for: {patient_data}",
                context={"category": category.value}
            )

        # 5. Format final output
        final_response = await self.output_formatter.arun(
            f"Format recommendation for: {json.dumps(context.__dict__)}",
            context={"formatted_context": context}
        )

        return final_response

    def _determine_category(self, patient_data: Dict[str, Any]) -> InfectionCategory:
        """Determine the most likely infection category"""
        infection_type = patient_data.get('infection_type', '').lower()

        # Simple mapping - can be enhanced with ML classification
        category_map = {
            'pneumonia': InfectionCategory.PNEUMONIA,
            'uti': InfectionCategory.UTI,
            'cystitis': InfectionCategory.UTI,
            'pyelonephritis': InfectionCategory.UTI,
            'skin': InfectionCategory.SKIN_SOFT_TISSUE,
            'cellulitis': InfectionCategory.SKIN_SOFT_TISSUE,
            'ssti': InfectionCategory.SKIN_SOFT_TISSUE,
            'intra': InfectionCategory.INTRA_ABDOMINAL,
            'bone': InfectionCategory.BONE_JOINT,
            'joint': InfectionCategory.BONE_JOINT,
            'meningitis': InfectionCategory.MENINGITIS,
            'bacteremia': InfectionCategory.BACTEREMIA_SEPSIS,
            'sepsis': InfectionCategory.BACTEREMIA_SEPSIS,
        }

        return category_map.get(infection_type, InfectionCategory.GENERAL)

    def _needs_evidence(self, response: Any) -> bool:
        """Determine if external evidence is needed"""
        # Check for uncertainty indicators in response
        content = response.content.lower()
        return any(indicator in content for indicator in [
            'uncertain', 'consider', 'may require', 'discuss with id'
        ])

    def _confidence_too_low(self, response: Any) -> bool:
        """Check if confidence is below threshold"""
        # Extract confidence from response or use heuristics
        return len(response.content) < 100  # Simple heuristic

    def _parse_evidence(self, response: Any) -> List[Dict]:
        """Parse evidence from search results"""
        # Implementation would parse PubMed/ArXiv results
        return []

class OutputFormattingAgent(Agent):
    """Final output formatting and presentation"""

    def __init__(self, **kwargs):
        super().__init__(
            name="Clinical_Output_Formatter",
            role="Formats final antibiotic recommendations for clinicians",
            instructions=[
                "Format responses in clinician-friendly structure",
                "Use clear sections with headers",
                "Highlight key information (dosing, rationale)",
                "Include confidence levels and evidence sources",
                "Follow TUHS formatting guidelines"
            ],
            **kwargs
        )

# Initialize the multi-agent system
async def create_tuhs_agent_system() -> Team:
    """Create the complete TUHS multi-agent system"""

    # Initialize vector database for TUHS guidelines
    vector_db = PgVector(
        table_name="tuhs_guidelines",
        db_url=VECTOR_DB_URL,
        search_type=SearchType.hybrid
    )

    # Create TUHS knowledge base
    tuhs_knowledge = PDFUrlKnowledgeBase(
        urls=["/path/to/ABXguideInp.json"],
        vector_db=vector_db
    )

    # Load knowledge base
    await tuhs_knowledge.aload(recreate=False)

    # Create category-specific agents
    category_agents = {}
    for category in InfectionCategory:
        if category != InfectionCategory.GENERAL:
            agent = TUHSCategoryAgent(
                category=category,
                model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
                knowledge=tuhs_knowledge,
                storage=PostgresStorage(table_name=f"tuhs_{category.value}_sessions", db_url=DB_URL),
                show_tool_calls=True,
                markdown=True
            )
            category_agents[category] = agent

    # Create specialized agents
    vector_agent = VectorMemoryAgent(
        model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
        knowledge=tuhs_knowledge,
        tools=[KnowledgeTools(knowledge=tuhs_knowledge)],
        storage=PostgresStorage(table_name="vector_backup_sessions", db_url=DB_URL)
    )

    evidence_agent = EvidenceSearchAgent(
        model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
        storage=PostgresStorage(table_name="evidence_sessions", db_url=DB_URL)
    )

    manager_agent = TUHSManagerAgent(
        category_agents=category_agents,
        model=OpenRouter(id="google/gemini-2.5-pro-preview"),
        storage=PostgresStorage(table_name="manager_sessions", db_url=DB_URL)
    )

    # Set references for manager
    manager_agent.vector_agent = vector_agent
    manager_agent.evidence_agent = evidence_agent

    output_formatter = OutputFormattingAgent(
        model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
        storage=PostgresStorage(table_name="formatter_sessions", db_url=DB_URL)
    )

    manager_agent.output_formatter = output_formatter

    # Create the team
    tuhs_team = Team(
        name="TUHS_Antibiotic_Stewardship_Team",
        mode="coordinate",
        model=OpenRouter(id="google/gemini-2.5-pro-preview"),
        members=list(category_agents.values()) + [vector_agent, evidence_agent, output_formatter],
        instructions=[
            "Coordinate between specialized TUHS agents",
            "Use category agents first, then evidence search",
            "Fall back to vector memory when needed",
            "Ensure all recommendations follow TUHS guidelines"
        ],
        success_criteria="Complete evidence-based antibiotic recommendation provided",
        enable_agentic_context=True,
        show_tool_calls=True,
        markdown=True
    )

    return tuhs_team

# Example usage
async def main():
    """Example usage of the TUHS multi-agent system"""

    # Create the system
    tuhs_team = await create_tuhs_agent_system()

    # Example patient case
    patient_data = {
        "age": 88,
        "gender": "M",
        "location": "Ward",
        "infection_type": "bacteremia",
        "history_mrsa": True,
        "history_vre": True,
        "gfr": 44,
        "allergies": "penicillin (rash)"
    }

    # Process the request
    response = await tuhs_team.arun(
        f"Provide antibiotic recommendation for: {json.dumps(patient_data)}",
        stream=True,
        show_full_reasoning=True
    )

    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
