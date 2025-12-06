"""
AI Council - Aletheia V2

Adversarial debate system with Prosecutor, Defender, and Jury.
The council debates the claim and produces a final verdict through voting.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()


class Vote(Enum):
    """Jury vote options."""
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class DebateArgument:
    """A single argument in the debate."""
    speaker: str  # "prosecutor" or "defender"
    round_num: int
    argument: str
    evidence_cited: List[str]
    confidence: float


@dataclass
class JurorVote:
    """Individual juror's vote and reasoning."""
    juror_id: str
    juror_persona: str
    vote: Vote
    confidence: float
    reasoning: str


@dataclass
class DebateRound:
    """A single round of debate."""
    round_num: int
    round_type: str  # "opening", "evidence_challenge", "rebuttal", "closing"
    prosecutor_argument: DebateArgument
    defender_argument: DebateArgument


@dataclass
class CouncilVerdict:
    """Final verdict from the AI Council."""
    claim: str
    verdict: Vote
    confidence: float
    vote_breakdown: Dict[str, int]  # {"TRUE": 2, "FALSE": 3, "UNCERTAIN": 0}
    juror_votes: List[JurorVote]
    debate_transcript: List[DebateRound]
    winning_arguments: List[str]
    key_evidence: List[str]
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# Juror personas for diverse perspectives
JUROR_PERSONAS = [
    {
        "id": "skeptic",
        "name": "The Skeptic",
        "description": "Requires strong evidence. High bar for proof. Distrusts sensational claims.",
        "temperature": 0.1
    },
    {
        "id": "pragmatist",
        "name": "The Pragmatist",
        "description": "Common sense approach. Weighs practical implications and real-world context.",
        "temperature": 0.4
    },
    {
        "id": "scientist",
        "name": "The Scientist",
        "description": "Data-driven analysis. Looks for statistical evidence and reproducibility.",
        "temperature": 0.1
    }
]


class Prosecutor:
    """Argues that the claim is FALSE."""
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )
    
    async def argue(
        self,
        claim: str,
        round_type: str,
        round_num: int,
        counter_evidence: Dict[str, Any],
        opponent_last_argument: Optional[str] = None
    ) -> DebateArgument:
        """Generate prosecutor's argument for this round."""
        
        context = f"""You are the PROSECUTOR in a fact-checking tribunal.
Your role: Argue that this claim is FALSE or MISLEADING.

CLAIM: "{claim}"

COUNTER-EVIDENCE AVAILABLE:
- Weak points: {counter_evidence.get('weak_points', [])}
- Counter-arguments: {counter_evidence.get('counter_arguments', [])}
- Contradicting sources: {len(counter_evidence.get('contradictions', []))} found

Round: {round_type.upper()} (Round {round_num})
"""
        
        if opponent_last_argument:
            context += f"\nDefender's last argument to counter:\n\"{opponent_last_argument}\"\n"
        
        prompts = {
            "opening": "Present your opening case for why this claim should be considered FALSE. Be compelling but factual.",
            "evidence_challenge": "Attack the weakest evidence supporting this claim. Point out gaps, biases, or logical flaws.",
            "rebuttal": "Respond to the Defender's arguments. Dismantle their case with counter-evidence.",
            "closing": "Deliver your closing statement. Summarize why the council should vote FALSE."
        }
        
        prompt = context + prompts.get(round_type, prompts["opening"])
        prompt += "\n\nRespond with your argument (2-3 paragraphs). Be persuasive but honest."
        
        response = self.llm.invoke([
            SystemMessage(content="You are a prosecutor arguing a claim is false. Be logical and evidence-based."),
            HumanMessage(content=prompt)
        ])
        
        return DebateArgument(
            speaker="prosecutor",
            round_num=round_num,
            argument=response.content.strip(),
            evidence_cited=counter_evidence.get('weak_points', [])[:3],
            confidence=counter_evidence.get('attack_strength', 0.5)
        )


class Defender:
    """Argues that the claim is TRUE."""
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )
    
    async def argue(
        self,
        claim: str,
        round_type: str,
        round_num: int,
        supporting_evidence: Dict[str, Any],
        opponent_last_argument: Optional[str] = None
    ) -> DebateArgument:
        """Generate defender's argument for this round."""
        
        sources = supporting_evidence.get('sources', [])
        sources_text = "\n".join([
            f"- {s.get('title', 'N/A')}: {s.get('content', '')[:500]}"
            for s in sources[:5]
        ]) if sources else "Multiple sources reviewed."
        
        context = f"""You are the DEFENDER in a fact-checking tribunal.
Your role: Argue that this claim is TRUE or LIKELY TRUE based on the evidence.

CLAIM: "{claim}"

SUPPORTING EVIDENCE FROM SEARCH RESULTS:
{sources_text}

Fact-checker preliminary verdict: {supporting_evidence.get('verdict', 'N/A')}
Evidence confidence: {supporting_evidence.get('confidence', 0.5):.1%}

Round: {round_type.upper()} (Round {round_num})
"""
        
        if opponent_last_argument:
            context += f"\nProsecutor's last argument to counter:\n\"{opponent_last_argument}\"\n"
        
        prompts = {
            "opening": "Present your opening case for why this claim should be considered TRUE. Cite your evidence.",
            "evidence_challenge": "Defend the evidence supporting this claim. Explain why the sources are credible.",
            "rebuttal": "Respond to the Prosecutor's attacks. Defend against their counter-arguments.",
            "closing": "Deliver your closing statement. Summarize why the council should vote TRUE."
        }
        
        prompt = context + prompts.get(round_type, prompts["opening"])
        prompt += "\n\nRespond with your argument (2-3 paragraphs). Be persuasive but honest."
        
        response = self.llm.invoke([
            SystemMessage(content="You are a defender arguing a claim is true. Be logical and evidence-based."),
            HumanMessage(content=prompt)
        ])
        
        return DebateArgument(
            speaker="defender",
            round_num=round_num,
            argument=response.content.strip(),
            evidence_cited=[s.get('title', '') for s in sources[:3]],
            confidence=supporting_evidence.get('confidence', 0.5)
        )


class Juror:
    """Independent juror who votes on the verdict."""
    
    def __init__(self, persona: Dict[str, Any]):
        self.persona = persona
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=persona.get("temperature", 0.2),
        )
    
    async def vote(
        self,
        claim: str,
        debate_transcript: List[DebateRound],
        supporting_evidence: Dict[str, Any] = None
    ) -> JurorVote:
        """Cast vote after reviewing the debate and evidence."""
        
        # Compile debate summary
        transcript_text = ""
        for round in debate_transcript:
            transcript_text += f"\n--- ROUND {round.round_num}: {round.round_type.upper()} ---\n"
            transcript_text += f"PROSECUTOR: {round.prosecutor_argument.argument[:500]}...\n"
            transcript_text += f"DEFENDER: {round.defender_argument.argument[:500]}...\n"
        
        # Include actual evidence summary
        evidence_text = ""
        if supporting_evidence:
            sources = supporting_evidence.get('sources', [])
            if sources:
                evidence_text = "\n\nDIRECT EVIDENCE FROM SEARCH RESULTS:\n"
                for s in sources[:3]:
                    evidence_text += f"- Source: {s.get('title', 'N/A')}\n"
                    evidence_text += f"  Content: {s.get('content', '')[:400]}\n"
        
        prompt = f"""You are {self.persona['name']}, a juror in a fact-checking tribunal.
Your persona: {self.persona['description']}

CLAIM BEING JUDGED: "{claim}"

DEBATE TRANSCRIPT:
{transcript_text}
{evidence_text}

Based on your persona, the arguments presented, AND the direct evidence, cast your vote:
- TRUE: The claim is accurate based on the evidence
- FALSE: The claim is inaccurate or contradicted by evidence
- UNCERTAIN: Cannot determine with confidence

IMPORTANT: Carefully read the direct evidence. If the evidence confirms the claim, vote TRUE.

Respond in JSON:
{{
    "vote": "TRUE" or "FALSE" or "UNCERTAIN",
    "confidence": <0.0-1.0>,
    "reasoning": "2-3 sentence explanation of your decision based on the evidence"
}}"""

        response = self.llm.invoke([
            SystemMessage(content=f"You are {self.persona['name']}. Vote based on your persona and the evidence."),
            HumanMessage(content=prompt)
        ])
        
        try:
            result = json.loads(re.search(r'\{.*\}', response.content, re.DOTALL).group())
            vote_str = result.get("vote", "UNCERTAIN").upper()
            
            try:
                vote = Vote[vote_str]
            except KeyError:
                vote = Vote.UNCERTAIN
            
            return JurorVote(
                juror_id=self.persona["id"],
                juror_persona=self.persona["name"],
                vote=vote,
                confidence=min(1.0, max(0.0, float(result.get("confidence", 0.5)))),
                reasoning=result.get("reasoning", "No reasoning provided.")
            )
            
        except:
            return JurorVote(
                juror_id=self.persona["id"],
                juror_persona=self.persona["name"],
                vote=Vote.UNCERTAIN,
                confidence=0.3,
                reasoning="Unable to parse vote."
            )


class AICouncil:
    """
    The AI Council: Adversarial debate system for fact-checking.
    
    Consists of:
    - Prosecutor: Argues claim is FALSE
    - Defender: Argues claim is TRUE
    - Jury: 5 jurors with different personas who vote independently
    """
    
    def __init__(self, num_rounds: int = 3):
        self.prosecutor = Prosecutor()
        self.defender = Defender()
        self.jurors = [Juror(persona) for persona in JUROR_PERSONAS]
        self.num_rounds = num_rounds
        self.round_types = ["opening", "evidence_challenge", "rebuttal", "closing"][:num_rounds]
    
    async def deliberate(
        self,
        claim: str,
        supporting_evidence: Dict[str, Any],
        counter_evidence: Dict[str, Any]
    ) -> CouncilVerdict:
        """
        Conduct full council deliberation.
        
        Args:
            claim: The claim being judged
            supporting_evidence: Evidence from fact-checker (for defender)
            counter_evidence: Evidence from devil's advocate (for prosecutor)
        """
        debate_transcript = []
        
        # Conduct debate rounds
        prosecutor_last = None
        defender_last = None
        
        for i, round_type in enumerate(self.round_types):
            round_num = i + 1
            
            # Prosecutor argues
            prosecutor_arg = await self.prosecutor.argue(
                claim=claim,
                round_type=round_type,
                round_num=round_num,
                counter_evidence=counter_evidence,
                opponent_last_argument=defender_last
            )
            
            # Defender argues
            defender_arg = await self.defender.argue(
                claim=claim,
                round_type=round_type,
                round_num=round_num,
                supporting_evidence=supporting_evidence,
                opponent_last_argument=prosecutor_arg.argument
            )
            
            debate_transcript.append(DebateRound(
                round_num=round_num,
                round_type=round_type,
                prosecutor_argument=prosecutor_arg,
                defender_argument=defender_arg
            ))
            
            prosecutor_last = prosecutor_arg.argument
            defender_last = defender_arg.argument
        
        # Jury votes - now with access to supporting evidence
        import asyncio
        votes = await asyncio.gather(*[
            juror.vote(claim, debate_transcript, supporting_evidence)
            for juror in self.jurors
        ])
        
        # Tally votes
        vote_breakdown = {"TRUE": 0, "FALSE": 0, "UNCERTAIN": 0}
        for vote in votes:
            vote_breakdown[vote.vote.value] += 1
        
        # Determine verdict
        if vote_breakdown["TRUE"] > vote_breakdown["FALSE"]:
            verdict = Vote.TRUE
        elif vote_breakdown["FALSE"] > vote_breakdown["TRUE"]:
            verdict = Vote.FALSE
        else:
            verdict = Vote.UNCERTAIN
        
        # Calculate confidence
        total_confidence = sum(v.confidence for v in votes)
        avg_confidence = total_confidence / len(votes) if votes else 0.5
        
        # Weight by vote agreement
        winning_votes = vote_breakdown[verdict.value]
        agreement_factor = winning_votes / len(votes)
        final_confidence = avg_confidence * agreement_factor
        
        # Identify winning arguments
        winning_arguments = []
        if verdict == Vote.FALSE:
            winning_arguments = counter_evidence.get('counter_arguments', [])[:3]
        elif verdict == Vote.TRUE:
            winning_arguments = [s.get('title', '') for s in supporting_evidence.get('sources', [])[:3]]
        
        # Generate summary
        summary = await self._generate_summary(
            claim, verdict, votes, debate_transcript
        )
        
        return CouncilVerdict(
            claim=claim,
            verdict=verdict,
            confidence=final_confidence,
            vote_breakdown=vote_breakdown,
            juror_votes=votes,
            debate_transcript=debate_transcript,
            winning_arguments=winning_arguments,
            key_evidence=[],
            summary=summary
        )
    
    async def _generate_summary(
        self,
        claim: str,
        verdict: Vote,
        votes: List[JurorVote],
        transcript: List[DebateRound]
    ) -> str:
        """Generate a summary of the council's decision."""
        
        vote_summary = ", ".join([
            f"{v.juror_persona}: {v.vote.value}"
            for v in votes
        ])
        
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
        )
        
        prompt = f"""Summarize the AI Council's decision:

CLAIM: "{claim}"
VERDICT: {verdict.value}
JURY VOTES: {vote_summary}

Write a 2-3 sentence summary explaining why the council reached this verdict.
Be factual and reference the key arguments that swayed the jury."""

        response = llm.invoke([
            SystemMessage(content="You summarize council decisions. Be concise and factual."),
            HumanMessage(content=prompt)
        ])
        
        return response.content.strip()
