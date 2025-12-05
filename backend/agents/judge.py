"""
Agent 3: The Judge - MoveH

The final arbiter that synthesizes evidence from both agents.
- Synthesizer: Normalizes inputs from Agent 1 and Agent 2
- Adjudicator: Applies Trust-Weighted Logic
- Reporter: Generates reasoning and Audit Evidence Package (AEP)
- Integrates ClaimProcessor for on-chain metadata
"""

import os
import json
import hashlib
import time
from datetime import datetime
from typing import TypedDict
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from agents.claim_processor import ClaimProcessor, ClaimType

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)


class JudgeState(TypedDict):
    """State for The Judge agent."""
    agent1_data: dict
    agent2_data: dict
    normalized_scores: dict
    weights: dict
    final_score: float
    verdict: str
    confidence_level: str
    reasoning: str
    claim_metadata: dict      # NEW: Processed claim metadata
    aep_package: dict


# Initialize ClaimProcessor
claim_processor = ClaimProcessor()


def generate_claim_hash(agent1_data: dict, agent2_data: dict) -> str:
    """Generate a unique hash for this claim."""
    content = json.dumps({
        "claim": agent1_data.get("original_claim", ""),
        "timestamp": datetime.now().isoformat(),
        "a1_verdict": agent1_data.get("preliminary_verdict", ""),
        "a2_score": agent2_data.get("integrity_score", 0)
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def calculate_confidence(score: float, agreement: bool) -> str:
    """Calculate confidence level based on score and agent agreement."""
    if agreement:
        if score >= 0.85 or score <= 0.15:
            return "VERY HIGH"
        elif score >= 0.7 or score <= 0.3:
            return "HIGH"
        else:
            return "MEDIUM"
    else:
        if score >= 0.6 or score <= 0.4:
            return "LOW"
        else:
            return "VERY LOW"


def synthesizer_node(state: JudgeState) -> JudgeState:
    """Normalize outputs from both agents into comparable metrics."""
    a1 = state["agent1_data"]
    a2 = state["agent2_data"]
    
    # Process claim metadata using ClaimProcessor
    original_claim = a1.get("original_claim", "")
    claim_metadata = claim_processor.process(original_claim)
    
    # Normalize Agent 1 (Fact Checker)
    a1_verdict = a1.get("preliminary_verdict", "UNVERIFIED")
    a1_evidence_sufficient = a1.get("evidence_sufficient", False)
    
    if a1_verdict == "VERIFIED":
        s1 = 1.0
        s1_confidence = "HIGH" if a1_evidence_sufficient else "MEDIUM"
    elif a1_verdict == "DEBUNKED":
        s1 = 0.0
        s1_confidence = "HIGH" if a1_evidence_sufficient else "MEDIUM"
    else:
        s1 = 0.5
        s1_confidence = "LOW"
    
    # Normalize Agent 2 (Forensic Expert)
    s2 = a2.get("integrity_score", 0.5)
    a2_verdict = a2.get("verdict", "UNKNOWN")
    
    if s2 >= 0.85 or s2 <= 0.15:
        s2_confidence = "HIGH"
    elif s2 >= 0.7 or s2 <= 0.3:
        s2_confidence = "MEDIUM"
    else:
        s2_confidence = "LOW"
    
    normalized = {
        "s1": s1,
        "s2": s2,
        "s1_verdict": a1_verdict,
        "s2_verdict": a2_verdict,
        "s1_confidence": s1_confidence,
        "s2_confidence": s2_confidence,
        "a1_evidence_sufficient": a1_evidence_sufficient,
        "a2_penalties": len(a2.get("penalties_applied", []))
    }
    
    return {**state, "normalized_scores": normalized, "claim_metadata": dict(claim_metadata)}


def adjudicator_node(state: JudgeState) -> JudgeState:
    """Apply Trust-Weighted Consensus Logic."""
    scores = state["normalized_scores"]
    s1 = scores["s1"]
    s2 = scores["s2"]
    a1_evidence = scores["a1_evidence_sufficient"]
    
    # Dynamic Weighting Logic
    if (s1 <= 0.1 or s1 >= 0.9) and a1_evidence:
        weight_facts = 0.85
        weight_forensics = 0.15
        weight_reason = "Definitive fact-check evidence found"
    elif s1 <= 0.2 or s1 >= 0.8:
        weight_facts = 0.70
        weight_forensics = 0.30
        weight_reason = "Fact-check found supporting evidence"
    elif s1 == 0.5:
        weight_facts = 0.25
        weight_forensics = 0.75
        weight_reason = "No factual evidence - relying on forensic analysis"
    else:
        weight_facts = 0.50
        weight_forensics = 0.50
        weight_reason = "Balanced weighting - mixed signals"
    
    final_score = (s1 * weight_facts) + (s2 * weight_forensics)
    
    # Agreement Check
    a1_direction = "positive" if s1 > 0.6 else "negative" if s1 < 0.4 else "neutral"
    a2_direction = "positive" if s2 > 0.6 else "negative" if s2 < 0.4 else "neutral"
    agents_agree = (a1_direction == a2_direction) or (a1_direction == "neutral") or (a2_direction == "neutral")
    
    # Determine Verdict with probability language
    truth_probability = final_score * 100  # Convert to percentage
    
    if final_score >= 0.75:
        verdict = "TRUE"
        verdict_text = f"{truth_probability:.0f}% likely to be true"
    elif final_score <= 0.25:
        verdict = "FALSE"
        verdict_text = f"{100 - truth_probability:.0f}% likely to be false"
    elif final_score >= 0.6:
        verdict = "PROBABLY_TRUE"
        verdict_text = f"{truth_probability:.0f}% likely to be true"
    elif final_score <= 0.4:
        verdict = "PROBABLY_FALSE"
        verdict_text = f"{100 - truth_probability:.0f}% likely to be false"
    else:
        verdict = "UNCERTAIN"
        verdict_text = "Cannot determine - insufficient evidence"
    
    confidence_level = calculate_confidence(final_score, agents_agree)
    
    if not agents_agree and a1_direction != "neutral" and a2_direction != "neutral":
        if verdict not in ["UNCERTAIN"]:
            verdict = "UNCERTAIN"
            verdict_text = "Conflicting signals - needs review"
            confidence_level = "LOW"
    
    weights = {
        "w1": weight_facts,
        "w2": weight_forensics,
        "reason": weight_reason,
        "agents_agree": agents_agree,
        "verdict_text": verdict_text,
        "truth_probability": truth_probability
    }
    
    return {
        **state,
        "weights": weights,
        "final_score": final_score,
        "verdict": verdict,
        "confidence_level": confidence_level
    }


def reporter_node(state: JudgeState) -> JudgeState:
    """Generate judicial reasoning and Audit Evidence Package."""
    verdict = state["verdict"]
    score = state["final_score"]
    confidence = state["confidence_level"]
    weights = state["weights"]
    scores = state["normalized_scores"]
    a1 = state["agent1_data"]
    a2 = state["agent2_data"]
    claim_meta = state.get("claim_metadata", {})
    
    a1_summary = f"""
    - Verdict: {scores['s1_verdict']}
    - Evidence Found: {a1.get('evidence_sufficient', False)}
    - Search Iterations: {a1.get('iterations', 1)}
    """
    
    a2_summary = f"""
    - Integrity Score: {scores['s2']:.2f}
    - Verdict: {scores['s2_verdict']}
    - Red Flags: {scores['a2_penalties']}
    """
    
    verdict_text = weights.get('verdict_text', verdict)
    
    prompt = f"""You are analyzing a claim for truthfulness.

VERDICT: {verdict_text}

FACT-CHECK RESULTS:
{a1_summary}

FORENSIC ANALYSIS:
{a2_summary}

Write a 2-sentence summary that:
1. States the probability of the claim being true/false (use % language)
2. Gives the user ONE key action they can take

Be direct and actionable. Example:
"This claim is 72% likely to be false based on contradicting news. Verify with official sources before sharing."
"""

    response = llm.invoke([
        SystemMessage(content="You are a neutral judge. Be concise and actionable."),
        HumanMessage(content=prompt)
    ])
    
    reasoning = response.content.strip()
    
    # Use claim_hash from ClaimProcessor instead of old method
    claim_hash = claim_meta.get("claim_hash", generate_claim_hash(a1, a2))[:16]
    
    aep = {
        "aep_version": "2.0",
        "claim_id": claim_hash,
        "timestamp": datetime.now().isoformat(),
        
        # NEW: On-chain metadata from ClaimProcessor
        "chain_metadata": {
            "claim_hash": claim_meta.get("claim_hash", ""),
            "claim_signature": claim_meta.get("claim_signature", ""),
            "keywords": claim_meta.get("keywords", []),
            "claim_type": claim_meta.get("claim_type", 2),
            "claim_type_name": claim_meta.get("claim_type_name", "BREAKING_NEWS"),
            "timestamp_unix": claim_meta.get("timestamp", int(time.time())),
            "expires_at": claim_meta.get("expires_at", 0),
            "freshness_hours": claim_meta.get("freshness_hours", 168),
        },
        
        "verdict": {
            "decision": verdict,
            "verdict_text": weights.get("verdict_text", ""),
            "truth_probability": weights.get("truth_probability", 50),
            "confidence_score": round(score, 4),
            "confidence_level": confidence
        },
        "reasoning": reasoning,
        "methodology": {
            "weights_used": {
                "fact_checker": weights["w1"],
                "forensic_expert": weights["w2"]
            },
            "weight_rationale": weights["reason"],
            "agents_in_agreement": weights["agents_agree"]
        },
        "evidence": {
            "agent_1_fact_checker": {
                "verdict": scores["s1_verdict"],
                "normalized_score": scores["s1"],
                "confidence": scores["s1_confidence"],
                "evidence_sufficient": scores["a1_evidence_sufficient"],
                "iterations": a1.get("iterations", 1),
                "queries_used": a1.get("search_queries_used", [])
            },
            "agent_2_forensic_expert": {
                "verdict": scores["s2_verdict"],
                "integrity_score": scores["s2"],
                "confidence": scores["s2_confidence"],
                "penalties_count": scores["a2_penalties"],
                "linguistic_summary": a2.get("linguistic_summary", {}),
                "detection_summary": a2.get("detection_summary", {})
            }
        },
        "storage": {
            "blockchain_ready": True,
            "shelby_ref": None,  # Will be set after upload
            "aptos_tx": None,    # Will be set after on-chain submission
        }
    }
    
    return {**state, "reasoning": reasoning, "aep_package": aep}


def build_judge_graph():
    """Build and compile The Judge LangGraph."""
    workflow = StateGraph(JudgeState)
    
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("adjudicator", adjudicator_node)
    workflow.add_node("reporter", reporter_node)
    
    workflow.set_entry_point("synthesizer")
    workflow.add_edge("synthesizer", "adjudicator")
    workflow.add_edge("adjudicator", "reporter")
    workflow.add_edge("reporter", END)
    
    return workflow.compile()


class TheJudge:
    """Agent 3: The Judge - Renders final verdict from agent evidence."""
    
    def __init__(self):
        self.graph = build_judge_graph()
    
    async def aadjudicate(self, agent1_output: dict, agent2_output: dict) -> dict:
        """Render a verdict asynchronously based on evidence from both agents."""
        initial_state: JudgeState = {
            "agent1_data": agent1_output,
            "agent2_data": agent2_output,
            "normalized_scores": {},
            "weights": {},
            "final_score": 0.0,
            "verdict": "",
            "confidence_level": "",
            "reasoning": "",
            "claim_metadata": {},
            "aep_package": {}
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state["aep_package"]
