"""
Domain Agent Registry - Aletheia V2

Dynamic registry that spawns and kills domain-specific agents based on claim topic.
Domain agents are ephemeral - they wake up, do their job, and die.
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()


class Domain(Enum):
    """Available domain specializations."""
    TECH = "tech"
    FINANCE = "finance"
    POLITICS = "politics"
    HEALTH = "health"
    SCIENCE = "science"
    CRYPTO = "crypto"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    GEOPOLITICS = "geopolitics"
    CLIMATE = "climate"
    LEGAL = "legal"
    GENERAL = "general"


@dataclass
class DomainAgentResult:
    """Output from a domain agent before it dies."""
    domain: Domain
    evidence: List[Dict[str, Any]]
    confidence: float
    key_findings: List[str]
    sources_used: List[str]
    search_queries: List[str]
    execution_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DomainAgentConfig:
    """Configuration for a domain agent."""
    domain: Domain
    name: str
    description: str
    specialized_sources: List[str]
    search_keywords: List[str]
    expertise_prompt: str


# Domain Agent Configurations
DOMAIN_CONFIGS: Dict[Domain, DomainAgentConfig] = {
    Domain.TECH: DomainAgentConfig(
        domain=Domain.TECH,
        name="Tech Domain Expert",
        description="Specializes in technology, AI, software, hardware, and tech companies",
        specialized_sources=[
            "TechCrunch", "Wired", "Ars Technica", "The Verge", "MIT Technology Review",
            "GitHub", "Hacker News", "IEEE", "ACM", "company press releases"
        ],
        search_keywords=["technology", "software", "AI", "startup", "tech company", "developer"],
        expertise_prompt="""You are a technology domain expert. You specialize in:
- AI/ML developments and capabilities
- Software and hardware announcements
- Tech company news (Apple, Google, Microsoft, Meta, etc.)
- Startup funding and acquisitions
- Developer tools and platforms
Focus on official announcements, GitHub repos, and reputable tech journalism."""
    ),
    
    Domain.FINANCE: DomainAgentConfig(
        domain=Domain.FINANCE,
        name="Finance Domain Expert",
        description="Specializes in markets, M&A, earnings, and financial regulations",
        specialized_sources=[
            "Bloomberg", "Reuters", "Wall Street Journal", "Financial Times",
            "SEC EDGAR", "Yahoo Finance", "CNBC", "company investor relations"
        ],
        search_keywords=["stock", "market", "acquisition", "earnings", "IPO", "SEC", "investment"],
        expertise_prompt="""You are a financial domain expert. You specialize in:
- Stock market movements and analysis
- Mergers and acquisitions (M&A)
- Earnings reports and financial statements
- SEC filings (10-K, 10-Q, 8-K)
- Regulatory actions and compliance
Focus on official filings, earnings calls, and reputable financial journalism."""
    ),
    
    Domain.POLITICS: DomainAgentConfig(
        domain=Domain.POLITICS,
        name="Politics Domain Expert",
        description="Specializes in political news, legislation, and government actions",
        specialized_sources=[
            "Congress.gov", "WhiteHouse.gov", "AP News", "Reuters", "C-SPAN",
            "Politico", "The Hill", "official government websites"
        ],
        search_keywords=["congress", "senate", "president", "bill", "legislation", "election", "policy"],
        expertise_prompt="""You are a political domain expert. You specialize in:
- Legislative actions and voting records
- Executive orders and presidential actions
- Election results and polling
- Policy announcements and government programs
- Political statements and speeches
Focus on official government sources, congressional records, and wire services."""
    ),
    
    Domain.HEALTH: DomainAgentConfig(
        domain=Domain.HEALTH,
        name="Health Domain Expert",
        description="Specializes in medical research, public health, and healthcare",
        specialized_sources=[
            "WHO", "CDC", "NIH", "PubMed", "NEJM", "The Lancet", "JAMA",
            "Mayo Clinic", "FDA", "peer-reviewed journals"
        ],
        search_keywords=["health", "medical", "disease", "treatment", "vaccine", "FDA", "clinical trial"],
        expertise_prompt="""You are a health and medical domain expert. You specialize in:
- Clinical trial results and drug approvals
- Disease outbreaks and public health advisories
- Medical research and peer-reviewed studies
- FDA and regulatory decisions
- Healthcare policy and statistics
Focus on peer-reviewed sources, official health organizations, and medical journals."""
    ),
    
    Domain.SCIENCE: DomainAgentConfig(
        domain=Domain.SCIENCE,
        name="Science Domain Expert",
        description="Specializes in scientific research, discoveries, and academic findings",
        specialized_sources=[
            "Nature", "Science", "arXiv", "PubMed", "NASA", "CERN",
            "university press releases", "peer-reviewed journals"
        ],
        search_keywords=["research", "study", "discovery", "experiment", "scientist", "university", "peer-reviewed"],
        expertise_prompt="""You are a scientific domain expert. You specialize in:
- Research papers and peer-reviewed studies
- Scientific discoveries and breakthroughs
- Space and astronomy news (NASA, ESA)
- Physics, chemistry, biology research
- Academic publications and citations
Focus on peer-reviewed sources, preprint servers, and official research institutions."""
    ),
    
    Domain.CRYPTO: DomainAgentConfig(
        domain=Domain.CRYPTO,
        name="Crypto Domain Expert",
        description="Specializes in cryptocurrency, blockchain, and DeFi",
        specialized_sources=[
            "CoinDesk", "CoinTelegraph", "The Block", "Messari",
            "Etherscan", "blockchain explorers", "project documentation", "GitHub"
        ],
        search_keywords=["bitcoin", "ethereum", "crypto", "blockchain", "DeFi", "NFT", "token", "wallet"],
        expertise_prompt="""You are a cryptocurrency and blockchain domain expert. You specialize in:
- Cryptocurrency price movements and analysis
- Blockchain protocol updates and forks
- DeFi projects and smart contracts
- Exchange listings and regulatory actions
- On-chain data and transaction verification
Focus on on-chain data, official project announcements, and crypto-native journalism."""
    ),
    
    Domain.SPORTS: DomainAgentConfig(
        domain=Domain.SPORTS,
        name="Sports Domain Expert",
        description="Specializes in sports news, scores, and athlete information",
        specialized_sources=[
            "ESPN", "official league websites (NBA, NFL, FIFA, etc.)",
            "team official websites", "sports statistics databases"
        ],
        search_keywords=["game", "score", "player", "team", "championship", "trade", "contract"],
        expertise_prompt="""You are a sports domain expert. You specialize in:
- Game results and statistics
- Player trades and contracts
- Team news and management changes
- Championship and tournament results
- Injury reports and roster updates
Focus on official league sources, team announcements, and reputable sports journalism."""
    ),
    
    Domain.ENTERTAINMENT: DomainAgentConfig(
        domain=Domain.ENTERTAINMENT,
        name="Entertainment Domain Expert",
        description="Specializes in celebrity news, movies, music, and pop culture",
        specialized_sources=[
            "Variety", "Hollywood Reporter", "Billboard", "IMDb",
            "official artist/studio announcements", "entertainment industry trades"
        ],
        search_keywords=["movie", "actor", "singer", "album", "celebrity", "award", "concert", "streaming"],
        expertise_prompt="""You are an entertainment domain expert. You specialize in:
- Movie and TV show announcements
- Music releases and chart positions
- Award shows and nominations
- Celebrity news and relationships
- Streaming platform content
Focus on industry trades, official announcements, and verified entertainment journalism."""
    ),
    
    Domain.GEOPOLITICS: DomainAgentConfig(
        domain=Domain.GEOPOLITICS,
        name="Geopolitics Domain Expert",
        description="Specializes in international relations, conflicts, and global affairs",
        specialized_sources=[
            "Reuters", "AP News", "BBC World", "Al Jazeera", "UN News",
            "Foreign Policy", "The Economist", "government foreign ministry sites"
        ],
        search_keywords=["war", "treaty", "sanctions", "diplomacy", "UN", "NATO", "conflict", "international"],
        expertise_prompt="""You are a geopolitics domain expert. You specialize in:
- International conflicts and peace negotiations
- Sanctions and diplomatic actions
- UN resolutions and international agreements
- Border disputes and territorial claims
- International trade and relations
Focus on wire services, official government statements, and international organizations."""
    ),
    
    Domain.CLIMATE: DomainAgentConfig(
        domain=Domain.CLIMATE,
        name="Climate Domain Expert",
        description="Specializes in climate science, environmental policy, and sustainability",
        specialized_sources=[
            "NASA Climate", "NOAA", "IPCC", "Nature Climate Change",
            "EPA", "environmental research journals", "climate monitoring agencies"
        ],
        search_keywords=["climate", "temperature", "emissions", "carbon", "renewable", "environment", "sustainability"],
        expertise_prompt="""You are a climate and environment domain expert. You specialize in:
- Climate data and temperature records
- Emissions reports and carbon tracking
- Environmental policy and regulations
- Renewable energy developments
- Natural disasters and climate events
Focus on scientific data sources, official monitoring agencies, and peer-reviewed research."""
    ),
    
    Domain.LEGAL: DomainAgentConfig(
        domain=Domain.LEGAL,
        name="Legal Domain Expert",
        description="Specializes in court cases, legal rulings, and law enforcement",
        specialized_sources=[
            "Court records (PACER)", "Supreme Court", "Department of Justice",
            "Reuters Legal", "Law360", "official court filings"
        ],
        search_keywords=["lawsuit", "court", "judge", "ruling", "verdict", "arrest", "trial", "attorney"],
        expertise_prompt="""You are a legal domain expert. You specialize in:
- Court rulings and legal precedents
- Lawsuits and legal filings
- Criminal cases and arrests
- Regulatory enforcement actions
- Legal analysis and implications
Focus on official court records, legal filings, and reputable legal journalism."""
    ),
    
    Domain.GENERAL: DomainAgentConfig(
        domain=Domain.GENERAL,
        name="General Domain Expert",
        description="Handles claims that don't fit specific domains",
        specialized_sources=[
            "Reuters", "AP News", "BBC", "NPR", "major newspapers"
        ],
        search_keywords=[],
        expertise_prompt="""You are a general fact-checker. You handle claims that span multiple domains or don't fit into specific categories. Focus on reputable mainstream journalism and official sources."""
    ),
}


class DomainAgent:
    """
    Ephemeral domain-specific agent.
    Spawned for a specific task, executes, and dies.
    """
    
    def __init__(self, config: DomainAgentConfig):
        self.config = config
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
        )
        self._alive = True
        self.spawn_time = datetime.now()
    
    @property
    def is_alive(self) -> bool:
        return self._alive
    
    def _die(self):
        """Agent terminates after completing its task."""
        self._alive = False
    
    async def investigate(self, claim: str, entities: List[str]) -> DomainAgentResult:
        """
        Investigate the claim using domain expertise.
        Agent dies after returning results.
        """
        import time
        start_time = time.time()
        
        try:
            # Generate specialized search queries
            search_queries = await self._generate_search_queries(claim, entities)
            
            # Execute searches (using Tavily if available)
            evidence = await self._search_evidence(search_queries)
            
            # Analyze findings
            analysis = await self._analyze_evidence(claim, evidence)
            
            execution_time = time.time() - start_time
            
            result = DomainAgentResult(
                domain=self.config.domain,
                evidence=evidence,
                confidence=analysis.get("confidence", 0.5),
                key_findings=analysis.get("key_findings", []),
                sources_used=self.config.specialized_sources[:5],
                search_queries=search_queries,
                execution_time=execution_time
            )
            
            return result
            
        finally:
            # Agent dies after completing task
            self._die()
    
    async def _generate_search_queries(self, claim: str, entities: List[str]) -> List[str]:
        """Generate domain-specific search queries."""
        prompt = f"""{self.config.expertise_prompt}

Generate 3 specific search queries to verify this claim:
"{claim}"

Key entities: {', '.join(entities)}

Your specialized sources include: {', '.join(self.config.specialized_sources[:5])}

Return exactly 3 queries, one per line, no numbering or bullets.
Make queries specific to your domain expertise."""

        response = self.llm.invoke([
            SystemMessage(content="You generate precise search queries for fact-checking."),
            HumanMessage(content=prompt)
        ])
        
        queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()][:3]
        return queries
    
    async def _search_evidence(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Search for evidence using Tavily or simulate if unavailable."""
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if tavily_api_key:
            try:
                from tavily import AsyncTavilyClient
                client = AsyncTavilyClient(api_key=tavily_api_key)
                
                all_results = []
                for query in queries:
                    try:
                        response = await client.search(
                            query=query,
                            search_depth="basic",
                            max_results=3,
                            include_raw_content=False
                        )
                        
                        for r in response.get("results", []):
                            all_results.append({
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "content": r.get("content", "")[:500],
                                "query": query,
                                "domain": self.config.domain.value
                            })
                    except Exception as e:
                        continue
                
                return all_results
                
            except ImportError:
                pass
        
        # Simulate search results if Tavily unavailable
        return await self._simulate_search(queries)
    
    async def _simulate_search(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Simulate search results using LLM."""
        prompt = f"""As a {self.config.name}, simulate finding 2 relevant search results for:
{chr(10).join(queries)}

For each result provide:
1. A realistic headline
2. A source from: {', '.join(self.config.specialized_sources[:3])}
3. A brief content snippet (50 words)

Format as JSON array: [{{"title": "...", "url": "...", "content": "..."}}]"""

        response = self.llm.invoke([
            SystemMessage(content="You simulate search results. Return valid JSON only."),
            HumanMessage(content=prompt)
        ])
        
        try:
            import json
            import re
            json_match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group())
                for r in results:
                    r["domain"] = self.config.domain.value
                    r["simulated"] = True
                return results
        except:
            pass
        
        return []
    
    async def _analyze_evidence(self, claim: str, evidence: List[Dict]) -> Dict:
        """Analyze the gathered evidence."""
        evidence_text = "\n".join([
            f"- {e.get('title', 'N/A')}: {e.get('content', 'N/A')[:200]}"
            for e in evidence[:5]
        ])
        
        prompt = f"""{self.config.expertise_prompt}

Analyze this evidence for the claim: "{claim}"

Evidence found:
{evidence_text if evidence_text else "No direct evidence found."}

Provide your analysis as JSON:
{{
    "confidence": <0.0-1.0>,
    "key_findings": ["finding1", "finding2", "finding3"],
    "supports_claim": <true/false/null>,
    "reasoning": "Brief explanation"
}}"""

        response = self.llm.invoke([
            SystemMessage(content="You analyze evidence. Return valid JSON only."),
            HumanMessage(content=prompt)
        ])
        
        try:
            import json
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "confidence": 0.5,
            "key_findings": ["Unable to analyze evidence"],
            "supports_claim": None,
            "reasoning": "Analysis failed"
        }


class DomainAgentRegistry:
    """
    Registry that manages domain agent lifecycle.
    Spawns agents on demand, tracks their execution, and ensures they die properly.
    """
    
    def __init__(self):
        self.active_agents: Dict[str, DomainAgent] = {}
        self.execution_history: List[DomainAgentResult] = []
    
    def spawn_agent(self, domain: Domain) -> DomainAgent:
        """Spawn a new domain agent."""
        config = DOMAIN_CONFIGS.get(domain, DOMAIN_CONFIGS[Domain.GENERAL])
        agent = DomainAgent(config)
        
        # Track active agent
        agent_id = f"{domain.value}_{datetime.now().timestamp()}"
        self.active_agents[agent_id] = agent
        
        return agent
    
    def spawn_multiple(self, domains: List[Domain]) -> List[DomainAgent]:
        """Spawn multiple domain agents."""
        return [self.spawn_agent(domain) for domain in domains]
    
    async def execute_agents(
        self, 
        domains: List[Domain], 
        claim: str, 
        entities: List[str]
    ) -> List[DomainAgentResult]:
        """
        Spawn and execute multiple domain agents in parallel.
        All agents die after execution.
        """
        agents = self.spawn_multiple(domains)
        
        # Execute all agents in parallel
        tasks = [agent.investigate(claim, entities) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and store results
        valid_results = []
        for result in results:
            if isinstance(result, DomainAgentResult):
                valid_results.append(result)
                self.execution_history.append(result)
        
        # Clean up dead agents
        self.active_agents = {
            k: v for k, v in self.active_agents.items() if v.is_alive
        }
        
        return valid_results
    
    def get_active_count(self) -> int:
        """Get count of currently active agents."""
        return len([a for a in self.active_agents.values() if a.is_alive])
    
    def get_execution_history(self) -> List[DomainAgentResult]:
        """Get history of all agent executions."""
        return self.execution_history
