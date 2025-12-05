"""
Aletheia Agents Package V2

Multi-agent fact-checking system with:
- Domain-specific ephemeral agents
- Adversarial debate (Devil's Advocate)
- AI Council with Prosecutor/Defender/Jury
- Claim triage and routing
"""

# Core agents (existing, enhanced)
from agents.fact_checker import FactChecker
from agents.forensic_expert import ForensicExpert
from agents.judge import TheJudge
from agents.claim_processor import ClaimProcessor, ClaimType, ClaimMetadata, is_verdict_fresh

# New V2 agents
from agents.claim_triage import ClaimTriageAgent, TriageResult, Complexity
from agents.domain_registry import (
    DomainAgentRegistry, 
    DomainAgent, 
    Domain, 
    DomainAgentResult,
    DOMAIN_CONFIGS
)
from agents.devils_advocate import DevilsAdvocate, DevilsAdvocateResult, CounterArgument
from agents.ai_council import (
    AICouncil,
    CouncilVerdict,
    Prosecutor,
    Defender,
    Juror,
    Vote,
    DebateRound,
    JurorVote
)

# Report generation
from agents.shelby import Shelby as ReportGenerator

__all__ = [
    # Core agents
    "FactChecker",
    "ForensicExpert", 
    "TheJudge",
    "ClaimProcessor",
    "ClaimType",
    "ClaimMetadata",
    "is_verdict_fresh",
    
    # V2: Triage
    "ClaimTriageAgent",
    "TriageResult",
    "Complexity",
    
    # V2: Domain agents
    "DomainAgentRegistry",
    "DomainAgent",
    "Domain",
    "DomainAgentResult",
    "DOMAIN_CONFIGS",
    
    # V2: Devil's Advocate
    "DevilsAdvocate",
    "DevilsAdvocateResult",
    "CounterArgument",
    
    # V2: AI Council
    "AICouncil",
    "CouncilVerdict",
    "Prosecutor",
    "Defender",
    "Juror",
    "Vote",
    "DebateRound",
    "JurorVote",
    
    # Report generation
    "ReportGenerator",
]
