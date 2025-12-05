"""
Claim Triage Agent - Aletheia V2

Router agent that:
1. Classifies claim complexity (simple/medium/complex)
2. Detects language and translates if needed
3. Extracts entities for downstream agents
4. Routes to appropriate domain agents
"""

import os
import re
import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from agents.domain_registry import Domain

load_dotenv()


class Complexity(Enum):
    """Claim complexity levels."""
    SIMPLE = "simple"      # Single fact, easy to verify
    MEDIUM = "medium"      # Multiple facts, requires cross-referencing
    COMPLEX = "complex"    # Multi-domain, requires extensive research


@dataclass
class TriageResult:
    """Result of claim triage analysis."""
    original_claim: str
    normalized_claim: str
    language: str
    needs_translation: bool
    translated_claim: str | None
    complexity: Complexity
    domains: List[Domain]
    entities: List[str]
    keywords: List[str]
    claim_type: str  # "factual", "opinion", "prediction", "historical"
    temporal_context: str | None  # "past", "present", "future"
    confidence: float


class ClaimTriageAgent:
    """
    Agent 0: The Triage Agent
    
    First agent in the pipeline. Analyzes incoming claims and routes them
    to appropriate domain agents.
    """
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
        )
    
    async def triage(self, claim: str) -> TriageResult:
        """
        Analyze and route a claim to appropriate handlers.
        """
        # Step 1: Normalize and detect language
        normalized, language, needs_translation, translated = await self._process_language(claim)
        
        # Use translated claim for analysis if needed
        analysis_claim = translated if translated else normalized
        
        # Step 2: Extract entities and keywords
        entities, keywords = await self._extract_entities(analysis_claim)
        
        # Step 3: Classify domains
        domains = await self._classify_domains(analysis_claim, entities, keywords)
        
        # Step 4: Determine complexity
        complexity = await self._assess_complexity(analysis_claim, domains, entities)
        
        # Step 5: Classify claim type and temporal context
        claim_type, temporal_context = await self._classify_claim_type(analysis_claim)
        
        return TriageResult(
            original_claim=claim,
            normalized_claim=normalized,
            language=language,
            needs_translation=needs_translation,
            translated_claim=translated,
            complexity=complexity,
            domains=domains,
            entities=entities,
            keywords=keywords,
            claim_type=claim_type,
            temporal_context=temporal_context,
            confidence=0.9 if not needs_translation else 0.8
        )
    
    async def _process_language(self, claim: str) -> Tuple[str, str, bool, str | None]:
        """Normalize claim and handle translation if needed."""
        # Basic normalization
        normalized = claim.strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        prompt = f"""Analyze this text and respond in JSON:
"{claim}"

{{
    "language": "<ISO 639-1 code, e.g., en, es, fr>",
    "needs_translation": <true if not English, false otherwise>,
    "english_translation": "<translation if needed, null if already English>"
}}"""

        response = self.llm.invoke([
            SystemMessage(content="You detect language and translate. Return valid JSON only."),
            HumanMessage(content=prompt)
        ])
        
        try:
            result = json.loads(re.search(r'\{.*\}', response.content, re.DOTALL).group())
            return (
                normalized,
                result.get("language", "en"),
                result.get("needs_translation", False),
                result.get("english_translation")
            )
        except:
            return normalized, "en", False, None
    
    async def _extract_entities(self, claim: str) -> Tuple[List[str], List[str]]:
        """Extract named entities and keywords from the claim."""
        prompt = f"""Extract entities and keywords from this claim:
"{claim}"

Respond in JSON:
{{
    "entities": ["list of named entities - people, companies, places, products"],
    "keywords": ["list of important keywords/terms for searching"]
}}

Example:
Claim: "Elon Musk announced Tesla will acquire Twitter for $50 billion"
{{
    "entities": ["Elon Musk", "Tesla", "Twitter"],
    "keywords": ["acquisition", "50 billion", "announce"]
}}"""

        response = self.llm.invoke([
            SystemMessage(content="You extract entities. Return valid JSON only."),
            HumanMessage(content=prompt)
        ])
        
        try:
            result = json.loads(re.search(r'\{.*\}', response.content, re.DOTALL).group())
            return (
                result.get("entities", []),
                result.get("keywords", [])
            )
        except:
            # Fallback: basic extraction
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim)
            return words[:5], []
    
    async def _classify_domains(
        self, 
        claim: str, 
        entities: List[str], 
        keywords: List[str]
    ) -> List[Domain]:
        """Classify which domains the claim belongs to."""
        
        domain_list = ", ".join([d.value for d in Domain if d != Domain.GENERAL])
        
        prompt = f"""Classify this claim into 1-3 relevant domains:
"{claim}"

Entities: {', '.join(entities)}
Keywords: {', '.join(keywords)}

Available domains: {domain_list}

Respond with JSON array of domain names (1-3 most relevant):
["domain1", "domain2"]

Rules:
- TECH: AI, software, hardware, tech companies
- FINANCE: stocks, markets, M&A, earnings
- POLITICS: government, elections, legislation
- HEALTH: medical, diseases, treatments
- SCIENCE: research, discoveries, academic
- CRYPTO: cryptocurrency, blockchain, DeFi
- SPORTS: games, players, teams
- ENTERTAINMENT: movies, music, celebrities
- GEOPOLITICS: international relations, conflicts
- CLIMATE: environment, weather, emissions
- LEGAL: lawsuits, court cases, regulations"""

        response = self.llm.invoke([
            SystemMessage(content="You classify domains. Return valid JSON array only."),
            HumanMessage(content=prompt)
        ])
        
        try:
            domains_str = json.loads(re.search(r'\[.*\]', response.content, re.DOTALL).group())
            domains = []
            for d in domains_str:
                try:
                    domains.append(Domain(d.lower()))
                except ValueError:
                    continue
            
            # Ensure at least one domain
            if not domains:
                domains = [Domain.GENERAL]
            
            return domains[:3]  # Max 3 domains
            
        except:
            return [Domain.GENERAL]
    
    async def _assess_complexity(
        self, 
        claim: str, 
        domains: List[Domain], 
        entities: List[str]
    ) -> Complexity:
        """Assess the complexity of verifying this claim."""
        
        prompt = f"""Assess the verification complexity of this claim:
"{claim}"

Domains involved: {', '.join([d.value for d in domains])}
Entities: {', '.join(entities)}

Complexity levels:
- SIMPLE: Single fact, one source can verify (e.g., "The Eiffel Tower is in Paris")
- MEDIUM: Multiple facts, needs cross-referencing (e.g., "Company X acquired Y for $Z")
- COMPLEX: Multi-domain, requires extensive research (e.g., "New policy will reduce emissions by 50%")

Respond with just one word: simple, medium, or complex"""

        response = self.llm.invoke([
            SystemMessage(content="You assess claim complexity. Return one word only."),
            HumanMessage(content=prompt)
        ])
        
        complexity_str = response.content.strip().lower()
        
        if "simple" in complexity_str:
            return Complexity.SIMPLE
        elif "complex" in complexity_str:
            return Complexity.COMPLEX
        else:
            return Complexity.MEDIUM
    
    async def _classify_claim_type(self, claim: str) -> Tuple[str, str | None]:
        """Classify the type of claim and its temporal context."""
        
        prompt = f"""Classify this claim:
"{claim}"

Respond in JSON:
{{
    "claim_type": "<factual|opinion|prediction|historical>",
    "temporal_context": "<past|present|future|null>"
}}

Types:
- factual: Verifiable statement of fact
- opinion: Subjective viewpoint or interpretation  
- prediction: Statement about future events
- historical: Statement about past events with specific dates"""

        response = self.llm.invoke([
            SystemMessage(content="You classify claims. Return valid JSON only."),
            HumanMessage(content=prompt)
        ])
        
        try:
            result = json.loads(re.search(r'\{.*\}', response.content, re.DOTALL).group())
            return (
                result.get("claim_type", "factual"),
                result.get("temporal_context")
            )
        except:
            return "factual", None
    
    def should_fast_track(self, triage_result: TriageResult) -> bool:
        """
        Determine if claim should be fast-tracked (skip some agents).
        Simple claims with high confidence don't need full council debate.
        """
        return (
            triage_result.complexity == Complexity.SIMPLE and
            len(triage_result.domains) == 1 and
            triage_result.claim_type == "factual"
        )
    
    def get_recommended_agents(self, triage_result: TriageResult) -> Dict[str, Any]:
        """
        Get recommended agent configuration based on triage.
        """
        base_config = {
            "domain_agents": triage_result.domains,
            "use_devils_advocate": True,
            "use_bias_detector": True,
            "use_council_debate": True,
            "council_rounds": 3
        }
        
        if triage_result.complexity == Complexity.SIMPLE:
            base_config["use_council_debate"] = False
            base_config["council_rounds"] = 1
        elif triage_result.complexity == Complexity.COMPLEX:
            base_config["council_rounds"] = 4
        
        # Adjust for claim type
        if triage_result.claim_type == "opinion":
            base_config["use_bias_detector"] = True
            base_config["opinion_flag"] = True
        elif triage_result.claim_type == "prediction":
            base_config["prediction_flag"] = True
            base_config["use_devils_advocate"] = True
        
        return base_config
