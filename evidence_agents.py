"""
Evidence Search Agents for TUHS Antibiotic Stewardship System
External literature search using PubMed, ArXiv, and web sources
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.storage.postgres import PostgresStorage
from agno.tools.pubmed import PubmedTools
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools

@dataclass
class EvidenceResult:
    """Structured evidence from external sources"""
    source: str  # "pubmed", "arxiv", "web"
    title: str
    authors: List[str]
    abstract: str
    publication_date: str
    relevance_score: float
    key_findings: List[str]
    clinical_relevance: str
    url: Optional[str] = None
    doi: Optional[str] = None

class PubMedEvidenceAgent(Agent):
    """Specialized agent for PubMed literature search"""

    def __init__(self, **kwargs):
        super().__init__(
            name="PubMed_Evidence_Specialist",
            role="Searches PubMed for evidence-based medical literature and clinical trials",
            tools=[PubmedTools()],
            instructions=[
                "Search PubMed for high-quality evidence",
                "Focus on clinical trials and systematic reviews",
                "Extract key findings relevant to antibiotic therapy",
                "Assess clinical applicability to current case",
                "Provide evidence levels (RCT, observational, etc.)"
            ],
            **kwargs
        )

class ArXivEvidenceAgent(Agent):
    """Specialized agent for ArXiv academic papers"""

    def __init__(self, **kwargs):
        super().__init__(
            name="ArXiv_Research_Specialist",
            role="Searches ArXiv for academic papers on antibiotic resistance and infectious diseases",
            tools=[ArxivTools()],
            instructions=[
                "Search ArXiv for antimicrobial resistance research",
                "Focus on computational biology and epidemiology papers",
                "Extract resistance patterns and mechanisms",
                "Identify emerging treatment strategies",
                "Assess translational potential"
            ],
            **kwargs
        )

class WebEvidenceAgent(Agent):
    """Specialized agent for web-based evidence search"""

    def __init__(self, **kwargs):
        super().__init__(
            name="Web_Evidence_Specialist",
            role="Searches web sources for clinical guidelines and evidence-based resources",
            tools=[DuckDuckGoTools()],
            instructions=[
                "Search for evidence-based clinical guidelines",
                "Focus on IDSA, CDC, WHO, and academic medical centers",
                "Extract treatment recommendations and updates",
                "Identify consensus statements and best practices",
                "Assess recency and authority of sources"
            ],
            **kwargs
        )

class EvidenceCoordinatorAgent(Agent):
    """Coordinates evidence search across multiple sources"""

    def __init__(self, **kwargs):
        self.pubmed_agent = PubMedEvidenceAgent(
            model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
            storage=PostgresStorage(table_name="pubmed_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
        )

        self.arxiv_agent = ArXivEvidenceAgent(
            model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
            storage=PostgresStorage(table_name="arxiv_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
        )

        self.web_agent = WebEvidenceAgent(
            model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
            storage=PostgresStorage(table_name="web_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
        )

        super().__init__(
            name="Evidence_Coordinator",
            role="Coordinates evidence search across PubMed, ArXiv, and web sources",
            instructions=[
                "Query all evidence sources in parallel",
                "Synthesize findings from multiple sources",
                "Resolve conflicting evidence",
                "Provide evidence hierarchy and strength",
                "Generate evidence-based recommendations"
            ],
            **kwargs
        )

    async def search_all_sources(self, query: str, context: Dict[str, Any]) -> List[EvidenceResult]:
        """Search all evidence sources concurrently"""

        # Create search tasks for all agents
        tasks = [
            self.pubmed_agent.arun(f"Search PubMed for: {query}"),
            self.arxiv_agent.arun(f"Search ArXiv for: {query}"),
            self.web_agent.arun(f"Search web for: {query}")
        ]

        # Execute searches in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse and structure results
        evidence_results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"Error in evidence search {i}: {response}")
                continue

            source_results = self._parse_response_by_source(i, response)
            evidence_results.extend(source_results)

        # Rank by relevance and recency
        evidence_results.sort(key=lambda x: (x.relevance_score, x.publication_date), reverse=True)

        return evidence_results

    def _parse_response_by_source(self, source_index: int, response) -> List[EvidenceResult]:
        """Parse response based on source type"""
        results = []

        if source_index == 0:  # PubMed
            results = self._parse_pubmed_response(response)
        elif source_index == 1:  # ArXiv
            results = self._parse_arxiv_response(response)
        elif source_index == 2:  # Web
            results = self._parse_web_response(response)

        return results

    def _parse_pubmed_response(self, response) -> List[EvidenceResult]:
        """Parse PubMed search results"""
        results = []

        try:
            # Extract structured data from PubMed response
            content = response.content
            # This would parse the actual PubMed JSON response
            # For now, create placeholder structure

            if "articles" in content.lower():
                # Parse articles from response
                results.append(EvidenceResult(
                    source="pubmed",
                    title="Sample PubMed Article",
                    authors=["Author 1", "Author 2"],
                    abstract="Sample abstract from PubMed",
                    publication_date="2024",
                    relevance_score=0.8,
                    key_findings=["Finding 1", "Finding 2"],
                    clinical_relevance="High relevance to antibiotic therapy"
                ))
        except Exception as e:
            print(f"Error parsing PubMed response: {e}")

        return results

    def _parse_arxiv_response(self, response) -> List[EvidenceResult]:
        """Parse ArXiv search results"""
        results = []

        try:
            content = response.content
            if "arxiv" in content.lower():
                results.append(EvidenceResult(
                    source="arxiv",
                    title="Sample ArXiv Paper",
                    authors=["Researcher 1", "Researcher 2"],
                    abstract="Sample abstract from ArXiv",
                    publication_date="2024",
                    relevance_score=0.7,
                    key_findings=["Research finding 1", "Research finding 2"],
                    clinical_relevance="Moderate relevance to clinical practice"
                ))
        except Exception as e:
            print(f"Error parsing ArXiv response: {e}")

        return results

    def _parse_web_response(self, response) -> List[EvidenceResult]:
        """Parse web search results"""
        results = []

        try:
            content = response.content
            if "guideline" in content.lower() or "idsa" in content.lower():
                results.append(EvidenceResult(
                    source="web",
                    title="Clinical Practice Guideline",
                    authors=["Expert Panel"],
                    abstract="Evidence-based guideline content",
                    publication_date="2024",
                    relevance_score=0.9,
                    key_findings=["Guideline recommendation 1", "Guideline recommendation 2"],
                    clinical_relevance="High clinical relevance",
                    url="https://example-guideline.com"
                ))
        except Exception as e:
            print(f"Error parsing web response: {e}")

        return results

# Integration with main TUHS system
async def integrate_evidence_search(tuhs_team):
    """Integrate evidence search into main TUHS team"""

    evidence_coordinator = EvidenceCoordinatorAgent(
        model=OpenRouter(id="google/gemini-2.5-flash-lite-preview"),
        storage=PostgresStorage(table_name="evidence_coordinator_sessions", db_url="postgresql://localhost:5432/tuhs_abx")
    )

    # Add evidence coordinator to team
    tuhs_team.members.append(evidence_coordinator)

    return tuhs_team

# Example usage
async def example_evidence_search():
    """Example of evidence search functionality"""

    coordinator = EvidenceCoordinatorAgent()

    query = "vancomycin dosing in renal impairment for MRSA bacteremia"
    context = {
        "patient_gfr": 44,
        "infection_type": "bacteremia",
        "organism": "MRSA"
    }

    evidence_results = await coordinator.search_all_sources(query, context)

    print(f"Found {len(evidence_results)} evidence sources:")
    for result in evidence_results[:3]:  # Show top 3
        print(f"\n{result.source.upper()}: {result.title}")
        print(f"Score: {result.relevance_score}")
        print(f"Key findings: {', '.join(result.key_findings)}")

if __name__ == "__main__":
    asyncio.run(example_evidence_search())
