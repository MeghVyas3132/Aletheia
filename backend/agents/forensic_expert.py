"""
Agent 2: The Forensic Expert - MoveH

Analyzes text for manipulation, AI generation, and fraud indicators.
- Profiler: Linguistic analysis (panic, urgency, typos, grammar)
- Detector: AI/bot patterns and manipulation tactics
- Auditor: Calculates integrity score with penalty system
"""

import os
import json
import re
from datetime import datetime
from typing import TypedDict
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)


class ForensicState(TypedDict):
    """State for the Forensic Expert agent."""
    raw_input: str
    linguistic_analysis: dict
    ai_detection: dict
    integrity_score: float
    penalties_applied: list
    forensic_log: dict


def extract_json_from_response(text: str) -> dict:
    """Safely extract JSON from LLM response."""
    try:
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    return {}


def count_urgency_markers(text: str) -> dict:
    """Count urgency and panic markers in text."""
    urgency_words = ['urgent', 'now', 'immediately', 'alert', 'warning', 'act fast', 
                     'limited time', 'hurry', 'don\'t wait', 'last chance', 'expires']
    panic_words = ['crisis', 'crash', 'collapse', 'disaster', 'emergency', 'critical',
                   'bankrupt', 'fraud', 'scam', 'hack', 'breach', 'stolen']
    
    text_lower = text.lower()
    return {
        "urgency_words": sum(1 for word in urgency_words if word in text_lower),
        "panic_words": sum(1 for word in panic_words if word in text_lower),
        "exclamations": text.count('!'),
        "caps_ratio": round(sum(1 for c in text if c.isupper()) / max(len(text), 1), 3)
    }


def profiler_node(state: ForensicState) -> ForensicState:
    """Perform deep linguistic analysis."""
    text = state["raw_input"]
    markers = count_urgency_markers(text)
    
    prompt = f"""Analyze this text for signs of manipulation or unprofessionalism:

TEXT: \"\"\"{text}\"\"\"

Evaluate:
1. URGENCY_LEVEL (0-10): Pressure for immediate action
2. GRAMMAR_QUALITY (0-10): Professional writing quality
3. TONE_TYPE: "professional", "sensationalist", "threatening", or "informal"
4. CREDIBILITY_MARKERS: "high", "medium", or "low"
5. SPECIFIC_ISSUES: List any problems found

Respond in JSON:
{{
    "urgency_level": <0-10>,
    "grammar_quality": <0-10>,
    "tone_type": "<type>",
    "credibility_markers": "<level>",
    "specific_issues": ["issue1", "issue2"],
    "reasoning": "Brief explanation"
}}"""

    response = llm.invoke([
        SystemMessage(content="You are an expert forensic linguist. Always respond with valid JSON."),
        HumanMessage(content=prompt)
    ])
    
    llm_analysis = extract_json_from_response(response.content)
    
    analysis = {
        "urgency_level": llm_analysis.get("urgency_level", 5),
        "grammar_quality": llm_analysis.get("grammar_quality", 5),
        "tone_type": llm_analysis.get("tone_type", "informal"),
        "credibility_markers": llm_analysis.get("credibility_markers", "medium"),
        "specific_issues": llm_analysis.get("specific_issues", []),
        "reasoning": llm_analysis.get("reasoning", "Analysis completed"),
        "marker_counts": markers
    }
    
    return {**state, "linguistic_analysis": analysis}


def detector_node(state: ForensicState) -> ForensicState:
    """Scan for AI generation, bot behavior, and manipulation tactics."""
    text = state["raw_input"]
    
    prompt = f"""Analyze this text for AI generation or manipulation:

TEXT: \"\"\"{text}\"\"\"

Evaluate:
1. AI_PROBABILITY (0.0-1.0): Likelihood text was AI-generated
2. BOT_PATTERNS: "none", "template", or "spam"
3. MANIPULATION_TACTICS: List tactics found (fear, urgency, false authority, etc.)
4. SCAM_INDICATORS: Common scam red flags

Respond in JSON:
{{
    "ai_probability": <0.0-1.0>,
    "bot_patterns": "<pattern>",
    "manipulation_tactics": ["tactic1", "tactic2"],
    "scam_indicators": ["indicator1"],
    "confidence": "<high|medium|low>",
    "reasoning": "Brief explanation"
}}"""

    response = llm.invoke([
        SystemMessage(content="You are an expert in AI detection. Always respond with valid JSON."),
        HumanMessage(content=prompt)
    ])
    
    llm_detection = extract_json_from_response(response.content)
    
    detection = {
        "ai_probability": llm_detection.get("ai_probability", 0.5),
        "bot_patterns": llm_detection.get("bot_patterns", "none"),
        "manipulation_tactics": llm_detection.get("manipulation_tactics", []),
        "scam_indicators": llm_detection.get("scam_indicators", []),
        "confidence": llm_detection.get("confidence", "medium"),
        "reasoning": llm_detection.get("reasoning", "Analysis completed")
    }
    
    return {**state, "ai_detection": detection}


def auditor_node(state: ForensicState) -> ForensicState:
    """Calculate integrity score using weighted penalty system."""
    linguistic = state["linguistic_analysis"]
    detection = state["ai_detection"]
    
    score = 1.0
    penalties = []
    
    # Urgency Penalty (max -0.25)
    urgency = linguistic.get("urgency_level", 0)
    if urgency >= 8:
        penalties.append(("Extreme Urgency", 0.25))
    elif urgency >= 6:
        penalties.append(("High Urgency", 0.15))
    elif urgency >= 4:
        penalties.append(("Moderate Urgency", 0.05))
    
    # Grammar Penalty (max -0.30)
    grammar = linguistic.get("grammar_quality", 10)
    if grammar <= 3:
        penalties.append(("Poor Grammar", 0.30))
    elif grammar <= 5:
        penalties.append(("Fair Grammar", 0.15))
    elif grammar <= 7:
        penalties.append(("Minor Grammar Issues", 0.05))
    
    # Tone Penalty (max -0.20)
    tone = linguistic.get("tone_type", "professional")
    if tone == "threatening":
        penalties.append(("Threatening Tone", 0.20))
    elif tone == "sensationalist":
        penalties.append(("Sensationalist Tone", 0.15))
    elif tone == "informal":
        penalties.append(("Informal Tone", 0.05))
    
    # Credibility Penalty (max -0.15)
    credibility = linguistic.get("credibility_markers", "medium")
    if credibility == "low":
        penalties.append(("Low Credibility", 0.15))
    elif credibility == "medium":
        penalties.append(("Medium Credibility", 0.05))
    
    # AI/Bot Penalty (max -0.25)
    ai_prob = detection.get("ai_probability", 0)
    if ai_prob >= 0.7:
        penalties.append(("High AI Probability", 0.25))
    elif ai_prob >= 0.5:
        penalties.append(("Moderate AI Probability", 0.15))
    elif ai_prob >= 0.3:
        penalties.append(("Low AI Probability", 0.05))
    
    # Bot Pattern Penalty (max -0.20)
    bot_pattern = detection.get("bot_patterns", "none")
    if bot_pattern == "spam":
        penalties.append(("Spam Bot Patterns", 0.20))
    elif bot_pattern == "template":
        penalties.append(("Template Bot Patterns", 0.10))
    
    # Manipulation Tactics Penalty (max -0.30)
    tactics = detection.get("manipulation_tactics", [])
    if len(tactics) >= 3:
        penalties.append((f"Multiple Manipulation Tactics ({len(tactics)})", 0.30))
    elif len(tactics) >= 1:
        penalties.append((f"Manipulation Tactics ({len(tactics)})", 0.15))
    
    # Scam Indicators Penalty (max -0.35)
    scam = detection.get("scam_indicators", [])
    if len(scam) >= 3:
        penalties.append((f"Multiple Scam Indicators ({len(scam)})", 0.35))
    elif len(scam) >= 1:
        penalties.append((f"Scam Indicators ({len(scam)})", 0.20))
    
    total_penalty = sum(p[1] for p in penalties)
    score = max(0.0, score - total_penalty)
    
    # Determine verdict
    if score >= 0.85:
        verdict = "HIGH INTEGRITY"
        confidence = "High confidence - appears legitimate"
    elif score >= 0.70:
        verdict = "LIKELY LEGITIMATE"
        confidence = "Moderate confidence - minor concerns"
    elif score >= 0.50:
        verdict = "SUSPICIOUS"
        confidence = "Low confidence - significant red flags"
    elif score >= 0.30:
        verdict = "LIKELY FRAUDULENT"
        confidence = "High confidence - multiple fraud indicators"
    else:
        verdict = "CONFIRMED SCAM"
        confidence = "Very high confidence - definite fraud pattern"
    
    forensic_log = {
        "integrity_score": round(score, 3),
        "verdict": verdict,
        "confidence": confidence,
        "penalties_applied": penalties,
        "total_penalty": round(total_penalty, 3),
        "linguistic_summary": {
            "urgency": linguistic.get("urgency_level"),
            "grammar": linguistic.get("grammar_quality"),
            "tone": linguistic.get("tone_type"),
            "credibility": linguistic.get("credibility_markers"),
            "issues": linguistic.get("specific_issues", [])
        },
        "detection_summary": {
            "ai_probability": detection.get("ai_probability"),
            "bot_patterns": detection.get("bot_patterns"),
            "manipulation_tactics": detection.get("manipulation_tactics", []),
            "scam_indicators": detection.get("scam_indicators", [])
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return {
        **state,
        "integrity_score": score,
        "penalties_applied": penalties,
        "forensic_log": forensic_log
    }


def build_forensic_graph():
    """Build and compile the Forensic Expert LangGraph."""
    workflow = StateGraph(ForensicState)
    
    workflow.add_node("profiler", profiler_node)
    workflow.add_node("detector", detector_node)
    workflow.add_node("auditor", auditor_node)
    
    workflow.set_entry_point("profiler")
    workflow.add_edge("profiler", "detector")
    workflow.add_edge("detector", "auditor")
    workflow.add_edge("auditor", END)
    
    return workflow.compile()


class ForensicExpert:
    """Agent 2: The Forensic Expert - Analyzes text for fraud indicators."""
    
    def __init__(self):
        self.graph = build_forensic_graph()
    
    async def astream_analyze(self, text: str):
        """Analyze text asynchronously and yield state updates."""
        initial_state: ForensicState = {
            "raw_input": text,
            "linguistic_analysis": {},
            "ai_detection": {},
            "integrity_score": 0.0,
            "penalties_applied": [],
            "forensic_log": {}
        }
        async for event in self.graph.astream(initial_state):
            yield event
