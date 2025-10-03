"""
Complete TUHS Multi-Agent Antibiotic Stewardship System
Integration of all components with proper Agno architecture
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

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

# Import our custom modules
from tuhs_multi_agent_system import (
    InfectionCategory, TUHSCategoryAgent, VectorMemoryAgent,
    AgentContext, create_tuhs_agent_system
)
from evidence_agents import EvidenceCoordinatorAgent
from enhanced_manager_formatter import EnhancedTUHSManager, EnhancedOutputFormatter

class CompleteTUHSSystem:
    """Complete TUHS antibiotic stewardship system with all components"""

    def __init__(self, db_url: str = "postgresql://localhost:5432/tuhs_abx"):
        self.db_url = db_url
        self.team: Optional[Team] = None
        self.knowledge_base = None
        self.category_agents: Dict[InfectionCategory, TUHSCategoryAgent] = {}

    async def initialize(self):
        """Initialize the complete system"""

        print("🚀 Initializing TUHS Multi-Agent System...")

        # 1. Setup knowledge base
        await self._setup_knowledge_base()

        # 2. Create category agents
        await self._create_category_agents()

        # 3. Create evidence agents
        self.evidence_coordinator = EvidenceCoordinatorAgent(
            model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
            storage=PostgresStorage(table_name="evidence_coordinator_sessions", db_url=self.db_url)
        )

        # 4. Create manager and formatter
        self.manager = EnhancedTUHSManager(
            category_agents=self.category_agents,
            model=OpenRouter(id="google/gemini-2.5-pro-preview"),
            storage=PostgresStorage(table_name="manager_sessions", db_url=self.db_url)
        )

        self.formatter = EnhancedOutputFormatter(
            model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
            storage=PostgresStorage(table_name="formatter_sessions", db_url=self.db_url)
        )

        # 5. Create the complete team
        self.team = Team(
            name="Complete_TUHS_Stewardship_System",
            mode="coordinate",
            model=OpenRouter(id="google/gemini-2.5-pro-preview"),
            members=[
                self.manager,
                self.formatter,
                self.evidence_coordinator
            ] + list(self.category_agents.values()),
            instructions=[
                "Coordinate complete antibiotic stewardship workflow",
                "Use TUHS category agents as primary source",
                "Supplement with evidence-based literature when needed",
                "Provide structured, clinician-friendly output",
                "Maintain context and metadata throughout workflow"
            ],
            success_criteria="Complete evidence-based recommendation with confidence assessment",
            enable_agentic_context=True,
            show_tool_calls=True,
            markdown=True
        )

        print("✅ Complete TUHS System Initialized")

    async def _setup_knowledge_base(self):
        """Setup TUHS knowledge base"""
        vector_db = PgVector(
            table_name="tuhs_guidelines",
            db_url=self.db_url,
            search_type=SearchType.hybrid
        )

        # Load TUHS guidelines (you'll need to add your actual guideline files)
        self.knowledge_base = PDFUrlKnowledgeBase(
            urls=["/path/to/ABXguideInp.json"],  # Replace with actual path
            vector_db=vector_db
        )

        # Load knowledge base (comment out after first run)
        # await self.knowledge_base.aload(recreate=False)

    async def _create_category_agents(self):
        """Create category-specific agents"""
        for category in InfectionCategory:
            if category != InfectionCategory.GENERAL:
                agent = TUHSCategoryAgent(
                    category=category,
                    model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
                    knowledge=self.knowledge_base,
                    storage=PostgresStorage(table_name=f"tuhs_{category.value}_sessions", db_url=self.db_url),
                    show_tool_calls=True,
                    markdown=True
                )
                self.category_agents[category] = agent

    async def process_patient_case(self, patient_data: Dict[str, Any]) -> str:
        """Process a complete patient case"""

        if not self.team:
            await self.initialize()

        print(f"🔍 Processing case: {patient_data.get('infection_type', 'unknown')}")

        # Use enhanced manager for complete workflow
        recommendation = await self.manager.orchestrate_workflow(patient_data)

        # Format final output
        final_output = await self.formatter.format_recommendation(recommendation)

        print("✅ Case processed successfully")

        return final_output

    async def health_check(self) -> Dict[str, Any]:
        """System health check"""
        health = {
            "system_status": "healthy",
            "knowledge_base_loaded": self.knowledge_base is not None,
            "category_agents_count": len(self.category_agents),
            "evidence_agent_ready": self.evidence_coordinator is not None,
            "manager_ready": self.manager is not None,
            "formatter_ready": self.formatter is not None,
            "team_ready": self.team is not None
        }

        return health

# Example usage and testing
async def main():
    """Main function for testing the complete system"""

    # Initialize system
    tuhs_system = CompleteTUHSSystem()

    # Health check
    health = await tuhs_system.health_check()
    print("System Health Check:")
    for key, value in health.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")

    # Example patient cases
    test_cases = [
        {
            "age": 88,
            "gender": "M",
            "location": "Ward",
            "infection_type": "pneumonia",
            "history_mrsa": False,
            "gfr": 45,
            "allergies": "none"
        },
        {
            "age": 65,
            "gender": "F",
            "location": "ICU",
            "infection_type": "uti",
            "history_resistance": "ESBL",
            "gfr": 25,
            "allergies": "penicillin (anaphylaxis)"
        },
        {
            "age": 72,
            "gender": "M",
            "location": "Ward",
            "infection_type": "skin",
            "history_mrsa": True,
            "gfr": 60,
            "allergies": "none"
        }
    ]

    # Process each test case
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {case['infection_type'].upper()}")
        print(f"{'='*60}")

        try:
            result = await tuhs_system.process_patient_case(case)
            print(result[:500] + "..." if len(result) > 500 else result)
        except Exception as e:
            print(f"❌ Error processing case {i}: {e}")

# CLI interface
def create_cli_interface():
    """Create a simple CLI interface for testing"""

    async def run_cli():
        system = CompleteTUHSSystem()

        print("🏥 TUHS Antibiotic Stewardship System")
        print("=" * 50)

        while True:
            print("\nOptions:")
            print("1. Process patient case")
            print("2. Health check")
            print("3. Exit")

            choice = input("\nSelect option: ").strip()

            if choice == "1":
                print("\nEnter patient data (JSON format):")
                print("Example: {\"age\": 88, \"infection_type\": \"pneumonia\", \"gfr\": 45}")

                try:
                    patient_json = input("Patient data: ")
                    patient_data = json.loads(patient_json)

                    result = await system.process_patient_case(patient_data)
                    print("\n" + "="*50)
                    print("RECOMMENDATION:")
                    print("="*50)
                    print(result)

                except json.JSONDecodeError:
                    print("❌ Invalid JSON format")
                except Exception as e:
                    print(f"❌ Error: {e}")

            elif choice == "2":
                health = await system.health_check()
                print("\nSystem Health:")
                for key, value in health.items():
                    status = "✅" if value else "❌"
                    print(f"  {status} {key}")

            elif choice == "3":
                print("👋 Goodbye!")
                break

            else:
                print("❌ Invalid option")

    # Run CLI
    asyncio.run(run_cli())

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        create_cli_interface()
    else:
        asyncio.run(main())
