"""
Devil's Advocate Agent - Aletheia V2

Adversarial agent that actively tries to DISPROVE claims.
Finds counter-arguments, contradicting sources, and attacks weak points.
"""

import os
import re
import json
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()


@dataclass
class CounterArgument:
    """A single counter-argument against the claim."""
    argument: str
    strength: float  # 0.0-1.0
    evidence: str
    source: str | None
    attack_type: str  # "logical", "evidential", "source_credibility", "temporal"


@dataclass 
class DevilsAdvocateResult:
    """Complete output from the Devil's Advocate agent."""
    original_claim: str
    counter_arguments: List[CounterArgument]
    weakest_points: List[str]
    contradicting_sources: List[Dict[str, Any]]
    overall_attack_strength: float  # 0.0-1.0 (how strong is the case against)
    summary: str
    recommendation: str  # "claim_likely_false", "claim_questionable", "claim_robust"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DevilsAdvocate:
    """
    Agent 3: The Devil's Advocate
    
    Adversarial agent that actively tries to disprove claims.
    Works opposite to the fact-checker - looks for reasons why the claim is FALSE.
    """
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,  # Slightly higher for creative counter-arguments
        )
    
    async def challenge(
        self, 
        claim: str, 
        supporting_evidence: List[Dict[str, Any]],
        entities: List[str]
    ) -> DevilsAdvocateResult:
        """
        Challenge the claim by finding counter-arguments.
        
        Args:
            claim: The claim to challenge
            supporting_evidence: Evidence gathered by fact-checker (to attack)
            entities: Key entities in the claim
        """
        # Step 1: Identify weak points in the claim
        weak_points = await self._identify_weak_points(claim, supporting_evidence)
        
        # Step 2: Search for contradicting evidence
        contradicting_sources = await self._find_contradictions(claim, entities)
        
        # Step 3: Generate counter-arguments
        counter_args = await self._generate_counter_arguments(
            claim, weak_points, supporting_evidence, contradicting_sources
        )
        
        # Step 4: Assess overall attack strength
        attack_strength, summary, recommendation = await self._assess_attack(
            claim, counter_args, contradicting_sources
        )
        
        return DevilsAdvocateResult(
            original_claim=claim,
            counter_arguments=counter_args,
            weakest_points=weak_points,
            contradicting_sources=contradicting_sources,
            overall_attack_strength=attack_strength,
            summary=summary,
            recommendation=recommendation
        )
    
    async def _identify_weak_points(
        self, 
        claim: str, 
        evidence: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify logical weak points and gaps in the claim."""
        
        evidence_summary = "\n".join([
            f"- {e.get('title', 'N/A')}: {e.get('content', '')[:150]}"
            for e in evidence[:5]
        ]) if evidence else "No supporting evidence provided."
        
        prompt = f"""You are a devil's advocate. Your job is to ATTACK this claim and find its weaknesses.

CLAIM: "{claim}"

SUPPORTING EVIDENCE PROVIDED:
{evidence_summary}

Identify 3-5 WEAK POINTS in this claim or its evidence:
- Logical gaps or assumptions
- Missing information
- Vague language that could be misleading
- Potential biases in sources
- Temporal issues (outdated? too recent to verify?)
- Numbers that seem suspicious

Return as JSON array of strings:
["weak point 1", "weak point 2", ...]"""

        response = self.llm.invoke([
            SystemMessage(content="You find weaknesses in claims. Be skeptical. Return JSON array."),
            HumanMessage(content=prompt)
        ])
        
        try:
            return json.loads(re.search(r'\[.*\]', response.content, re.DOTALL).group())
        except:
            return ["Unable to identify specific weak points"]
    
    async def _find_contradictions(
        self, 
        claim: str, 
        entities: List[str]
    ) -> List[Dict[str, Any]]:
        """Search for sources that contradict the claim."""
        
        # Generate counter-search queries
        prompt = f"""Generate 3 search queries to find information that CONTRADICTS this claim:
"{claim}"

Key entities: {', '.join(entities)}

Think about:
- Opposite claims or denials
- Fact-checker debunks
- Official denials
- Competing narratives

Return 3 queries, one per line, no numbering."""

        response = self.llm.invoke([
            SystemMessage(content="You generate queries to find contradicting evidence."),
            HumanMessage(content=prompt)
        ])
        
        queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()][:3]
        
        # Search for contradicting evidence
        contradictions = await self._search_contradictions(queries)
        
        return contradictions
    
    async def _search_contradictions(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Search for contradicting sources."""
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
                            max_results=2,
                            include_raw_content=False
                        )
                        
                        for r in response.get("results", []):
                            all_results.append({
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "content": r.get("content", "")[:300],
                                "query": query,
                                "type": "contradiction_search"
                            })
                    except:
                        continue
                
                return all_results
                
            except ImportError:
                pass
        
        # Simulate if Tavily unavailable
        return await self._simulate_contradictions(queries)
    
    async def _simulate_contradictions(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Simulate finding contradicting sources."""
        prompt = f"""As a devil's advocate, simulate finding 2 sources that CONTRADICT or QUESTION these claims:
Queries: {', '.join(queries)}

Return JSON array:
[{{"title": "Headline that contradicts", "content": "Why this contradicts the claim", "source": "Example source"}}]"""

        response = self.llm.invoke([
            SystemMessage(content="You simulate contradicting sources. Return valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            results = json.loads(re.search(r'\[.*\]', response.content, re.DOTALL).group())
            for r in results:
                r["simulated"] = True
            return results
        except:
            return []
    
    async def _generate_counter_arguments(
        self,
        claim: str,
        weak_points: List[str],
        supporting_evidence: List[Dict],
        contradictions: List[Dict]
    ) -> List[CounterArgument]:
        """Generate formal counter-arguments."""
        
        weak_points_text = "\n".join([f"- {wp}" for wp in weak_points])
        contradictions_text = "\n".join([
            f"- {c.get('title', 'N/A')}: {c.get('content', '')[:100]}"
            for c in contradictions[:3]
        ]) if contradictions else "No contradicting sources found."
        
        prompt = f"""You are building a case AGAINST this claim:
"{claim}"

WEAK POINTS IDENTIFIED:
{weak_points_text}

CONTRADICTING SOURCES:
{contradictions_text}

Generate 3 strong counter-arguments. For each, provide:
- The argument itself
- How strong it is (0.0-1.0)
- Evidence supporting this counter-argument
- Type: "logical", "evidential", "source_credibility", or "temporal"

Return as JSON array:
[
    {{
        "argument": "The counter-argument",
        "strength": 0.8,
        "evidence": "Why this counter-argument is valid",
        "attack_type": "logical"
    }}
]"""

        response = self.llm.invoke([
            SystemMessage(content="You build cases against claims. Return valid JSON array."),
            HumanMessage(content=prompt)
        ])
        
        try:
            args_data = json.loads(re.search(r'\[.*\]', response.content, re.DOTALL).group())
            counter_args = []
            
            for arg in args_data[:3]:
                counter_args.append(CounterArgument(
                    argument=arg.get("argument", ""),
                    strength=min(1.0, max(0.0, float(arg.get("strength", 0.5)))),
                    evidence=arg.get("evidence", ""),
                    source=arg.get("source"),
                    attack_type=arg.get("attack_type", "logical")
                ))
            
            return counter_args
            
        except:
            return [CounterArgument(
                argument="Unable to generate structured counter-arguments",
                strength=0.3,
                evidence="Analysis failed",
                source=None,
                attack_type="logical"
            )]
    
    async def _assess_attack(
        self,
        claim: str,
        counter_args: List[CounterArgument],
        contradictions: List[Dict]
    ) -> tuple[float, str, str]:
        """Assess overall strength of the attack on the claim."""
        
        # Calculate attack strength
        if not counter_args:
            attack_strength = 0.2
        else:
            attack_strength = sum(arg.strength for arg in counter_args) / len(counter_args)
        
        # Boost if we found real contradicting sources
        real_contradictions = [c for c in contradictions if not c.get("simulated", False)]
        if real_contradictions:
            attack_strength = min(1.0, attack_strength + 0.15)
        
        # Generate summary
        args_summary = "\n".join([
            f"- [{arg.attack_type}] {arg.argument} (strength: {arg.strength:.1f})"
            for arg in counter_args
        ])
        
        prompt = f"""As a devil's advocate, summarize your case against this claim:
"{claim}"

COUNTER-ARGUMENTS:
{args_summary}

CONTRADICTING SOURCES FOUND: {len(contradictions)}

Provide:
1. A 2-sentence summary of why this claim MIGHT be false
2. Your recommendation: "claim_likely_false", "claim_questionable", or "claim_robust"

Format:
SUMMARY: <your summary>
RECOMMENDATION: <one of the three options>"""

        response = self.llm.invoke([
            SystemMessage(content="You summarize attacks on claims. Be concise."),
            HumanMessage(content=prompt)
        ])
        
        content = response.content
        
        # Extract summary
        summary_match = re.search(r'SUMMARY:\s*(.+?)(?=RECOMMENDATION:|$)', content, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else "Attack analysis completed."
        
        # Extract recommendation
        if "claim_likely_false" in content.lower():
            recommendation = "claim_likely_false"
        elif "claim_questionable" in content.lower():
            recommendation = "claim_questionable"
        else:
            recommendation = "claim_robust"
        
        return attack_strength, summary, recommendation
