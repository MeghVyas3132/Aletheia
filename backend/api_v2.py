"""
Aletheia API V2 - AI Fact-Checking with Truth Market (OPTIMIZED)

Main API endpoints:
- /verify - Full multi-agent verification with council debate
- /verify_stream - Streaming version with real-time updates
- /market/* - Truth Market betting endpoints

OPTIMIZATIONS:
- Fast rule-based triage (0 LLM calls)
- Skip domain agents for simple claims
- Reduced debate rounds (2 instead of 3)
- Reduced jury size (3 instead of 5)
"""

import os
import logging
import asyncio
import json
import time
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Agents - Use fast triage
from agents import (
    FactChecker, ForensicExpert, TheJudge,
    DomainAgentRegistry, Domain,
    DevilsAdvocate, AICouncil, Vote,
    ReportGenerator, ClaimProcessor
)
from agents.claim_triage_fast import FastClaimTriage, get_fast_triage, Complexity

# Market
from market import (
    TruthMarketManager, get_market_manager,
    Market, Bet, BetPosition, ResolutionOutcome, MarketStatus
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Aletheia-API-V2")

# FastAPI app
app = FastAPI(
    title="Aletheia API V2",
    description="AI-Powered Fact-Checking with Truth Market",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)
app.mount("/download", StaticFiles(directory=STORAGE_DIR), name="download")

# Initialize agents - OPTIMIZED
fast_triage = get_fast_triage()  # Rule-based, no LLM
domain_registry = DomainAgentRegistry()
fact_checker = FactChecker()
forensic_expert = ForensicExpert()
devils_advocate = DevilsAdvocate()
ai_council = AICouncil(num_rounds=2)  # Reduced from 3 to 2
judge = TheJudge()
report_generator = ReportGenerator(storage_dir=STORAGE_DIR)
claim_processor = ClaimProcessor()

# Market manager
market_manager = get_market_manager()


# ==================== REQUEST MODELS ====================

class ClaimRequest(BaseModel):
    claim: str


class BetRequest(BaseModel):
    user_id: str
    market_id: str
    position: str  # "correct" or "wrong"
    amount: float


class UserRequest(BaseModel):
    username: str


class ResolveRequest(BaseModel):
    market_id: str
    outcome: str  # "aletheia_correct", "aletheia_wrong", "voided"
    source: str = ""
    evidence: str = ""


# ==================== HEALTH CHECK ====================

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Aletheia API V2",
        "version": "2.0.0",
        "features": [
            "Multi-agent fact-checking",
            "Domain-specific agents",
            "AI Council debate",
            "Truth Market betting"
        ]
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ==================== VERIFICATION ENDPOINTS ====================

@app.post("/verify_stream")
async def verify_claim_stream(request: ClaimRequest):
    """
    Full verification with streaming updates.
    Shows progress of each agent and council debate.
    """
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")

    start_time = time.time()

    async def event_generator():
        try:
            # Phase 1: Fast Triage (rule-based, NO LLM)
            yield f"data: {json.dumps({'type': 'status', 'phase': 'triage', 'message': 'Analyzing claim...'})}\n\n"
            
            triage_result = fast_triage.triage(claim)
            
            yield f"data: {json.dumps({'type': 'triage', 'data': {'domains': [d.value for d in triage_result.domains], 'complexity': triage_result.complexity.value, 'entities': triage_result.entities, 'claim_type': triage_result.claim_type}})}\n\n"
            
            # Phase 2: Domain Agents (ONLY for complex claims - skip for simple/medium)
            domain_evidence = []
            if triage_result.complexity == Complexity.COMPLEX:
                yield f"data: {json.dumps({'type': 'status', 'phase': 'domain_agents', 'message': f'Spawning {len(triage_result.domains)} domain agents...'})}\n\n"
                
                domain_results = await domain_registry.execute_agents(
                    domains=triage_result.domains,
                    claim=claim,
                    entities=triage_result.entities
                )
                
                for dr in domain_results:
                    domain_evidence.extend(dr.evidence)
                    yield f"data: {json.dumps({'type': 'domain_agent', 'domain': dr.domain.value, 'findings': dr.key_findings[:3], 'confidence': dr.confidence})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'phase': 'domain_agents', 'message': 'Simple claim - skipping domain agents'})}\n\n"
            
            # Phase 3: Core Agents (parallel)
            yield f"data: {json.dumps({'type': 'status', 'phase': 'core_agents', 'message': 'Running fact-checker and forensic expert...'})}\n\n"
            
            a1_result = {}
            a2_result = {}
            
            # Run fact checker
            async for event in fact_checker.astream_verify(claim):
                for node, state in event.items():
                    if node == "analyst" and "evidence_dossier" in state:
                        a1_result = state["evidence_dossier"]
                        yield f"data: {json.dumps({'type': 'agent', 'agent': 'FactChecker', 'verdict': a1_result.get('preliminary_verdict', 'N/A')})}\n\n"
            
            # Run forensic expert
            async for event in forensic_expert.astream_analyze(claim):
                for node, state in event.items():
                    if node == "auditor" and "forensic_log" in state:
                        a2_result = state["forensic_log"]
                        yield f"data: {json.dumps({'type': 'agent', 'agent': 'ForensicExpert', 'integrity_score': a2_result.get('integrity_score', 0)})}\n\n"
            
            # Combine domain evidence with fact-checker results
            if domain_evidence:
                existing_results = a1_result.get("search_results", [])
                a1_result["search_results"] = existing_results + domain_evidence
            
            # Phase 4: Devil's Advocate
            yield f"data: {json.dumps({'type': 'status', 'phase': 'devils_advocate', 'message': 'Devils Advocate challenging the claim...'})}\n\n"
            
            counter_evidence = await devils_advocate.challenge(
                claim=claim,
                supporting_evidence=a1_result.get("search_results", []),
                entities=triage_result.entities
            )
            
            yield f"data: {json.dumps({'type': 'devils_advocate', 'attack_strength': counter_evidence.overall_attack_strength, 'counter_arguments': [arg.argument for arg in counter_evidence.counter_arguments[:2]], 'recommendation': counter_evidence.recommendation})}\n\n"
            
            # Phase 5: AI Council Debate
            yield f"data: {json.dumps({'type': 'status', 'phase': 'council', 'message': 'AI Council convening for debate...'})}\n\n"
            
            supporting_evidence = {
                "sources": a1_result.get("search_results", []),
                "verdict": a1_result.get("preliminary_verdict", "UNVERIFIED"),
                "confidence": a1_result.get("evidence_sufficient", False) and 0.8 or 0.5
            }
            
            counter_evidence_dict = {
                "weak_points": counter_evidence.weakest_points,
                "counter_arguments": [arg.argument for arg in counter_evidence.counter_arguments],
                "contradictions": counter_evidence.contradicting_sources,
                "attack_strength": counter_evidence.overall_attack_strength
            }
            
            council_verdict = await ai_council.deliberate(
                claim=claim,
                supporting_evidence=supporting_evidence,
                counter_evidence=counter_evidence_dict
            )
            
            # Stream debate rounds
            for round in council_verdict.debate_transcript:
                yield f"data: {json.dumps({'type': 'debate_round', 'round': round.round_num, 'type': round.round_type, 'prosecutor': round.prosecutor_argument.argument[:200], 'defender': round.defender_argument.argument[:200]})}\n\n"
            
            # Stream jury votes
            for vote in council_verdict.juror_votes:
                yield f"data: {json.dumps({'type': 'jury_vote', 'juror': vote.juror_persona, 'vote': vote.vote.value, 'confidence': vote.confidence})}\n\n"
            
            # Phase 6: Final Verdict
            yield f"data: {json.dumps({'type': 'status', 'phase': 'verdict', 'message': 'Rendering final verdict...'})}\n\n"
            
            processing_time = time.time() - start_time
            
            # Map council verdict to response format
            verdict_map = {
                Vote.TRUE: "TRUE",
                Vote.FALSE: "FALSE",
                Vote.UNCERTAIN: "UNCERTAIN"
            }
            
            final_verdict = verdict_map.get(council_verdict.verdict, "UNCERTAIN")
            truth_probability = council_verdict.confidence * 100
            
            if final_verdict == "TRUE":
                truth_probability = 50 + (council_verdict.confidence * 50)
            elif final_verdict == "FALSE":
                truth_probability = 50 - (council_verdict.confidence * 50)
            else:
                truth_probability = 50
            
            # Generate report
            yield f"data: {json.dumps({'type': 'status', 'phase': 'report', 'message': 'Generating report...'})}\n\n"
            
            # Get claim ID
            claim_meta = claim_processor.process(claim)
            claim_id = claim_meta.get("claim_hash", "")[:16] if isinstance(claim_meta, dict) else str(hash(claim))[:16]
            
            # Build complete result
            complete_result = {
                "claim": claim,
                "claim_id": claim_id,
                "verdict": final_verdict,
                "confidence_score": council_verdict.confidence,
                "truth_probability": truth_probability,
                "verdict_text": council_verdict.summary,
                "council_vote": council_verdict.vote_breakdown,
                "debate_rounds": len(council_verdict.debate_transcript),
                "triage": {
                    "domains": [d.value for d in triage_result.domains],
                    "complexity": triage_result.complexity.value,
                    "entities": triage_result.entities
                },
                "devils_advocate": {
                    "attack_strength": counter_evidence.overall_attack_strength,
                    "recommendation": counter_evidence.recommendation
                },
                "sources": a1_result.get("search_results", [])[:5],
                "forensic_analysis": {
                    "integrity_score": a2_result.get("integrity_score", 0),
                    "verdict": a2_result.get("verdict", "UNKNOWN")
                },
                "processing_time": f"{processing_time:.1f}s"
            }
            
            # Create market for this claim
            category = triage_result.domains[0].value if triage_result.domains else "general"
            market = market_manager.create_market(
                claim=claim,
                aletheia_verdict=final_verdict,
                aletheia_confidence=council_verdict.confidence,
                verdict_summary=council_verdict.summary,
                category=category
            )
            complete_result["market_id"] = market.market_id
            complete_result["market"] = market.to_dict()
            
            yield f"data: {json.dumps({'type': 'result', 'data': complete_result})}\n\n"
            
        except Exception as e:
            logger.error(f"Verification error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/verify")
async def verify_claim(request: ClaimRequest):
    """
    Non-streaming verification endpoint.
    Returns complete result after all processing.
    """
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")
    
    start_time = time.time()
    
    try:
        # Fast Triage (rule-based)
        triage_result = fast_triage.triage(claim)
        
        # Domain agents (only for complex claims)
        domain_results = []
        if triage_result.complexity == Complexity.COMPLEX:
            domain_results = await domain_registry.execute_agents(
                domains=triage_result.domains,
                claim=claim,
                entities=triage_result.entities
            )
        
        # Core agents - run synchronously for simplicity
        a1_result = fact_checker.verify_claim(claim)
        a2_result = forensic_expert.analyze_text(claim)
        
        # Combine evidence
        domain_evidence = []
        for dr in domain_results:
            domain_evidence.extend(dr.evidence)
        
        if domain_evidence:
            a1_result["search_results"] = a1_result.get("search_results", []) + domain_evidence
        
        # Devil's Advocate
        counter_evidence = await devils_advocate.challenge(
            claim=claim,
            supporting_evidence=a1_result.get("search_results", []),
            entities=triage_result.entities
        )
        
        # AI Council
        supporting_evidence = {
            "sources": a1_result.get("search_results", []),
            "verdict": a1_result.get("preliminary_verdict", "UNVERIFIED"),
            "confidence": 0.7
        }
        
        counter_evidence_dict = {
            "weak_points": counter_evidence.weakest_points,
            "counter_arguments": [arg.argument for arg in counter_evidence.counter_arguments],
            "contradictions": counter_evidence.contradicting_sources,
            "attack_strength": counter_evidence.overall_attack_strength
        }
        
        council_verdict = await ai_council.deliberate(
            claim=claim,
            supporting_evidence=supporting_evidence,
            counter_evidence=counter_evidence_dict
        )
        
        processing_time = time.time() - start_time
        
        # Map verdict
        verdict_map = {Vote.TRUE: "TRUE", Vote.FALSE: "FALSE", Vote.UNCERTAIN: "UNCERTAIN"}
        final_verdict = verdict_map.get(council_verdict.verdict, "UNCERTAIN")
        
        # Create market
        category = triage_result.domains[0].value if triage_result.domains else "general"
        market = market_manager.create_market(
            claim=claim,
            aletheia_verdict=final_verdict,
            aletheia_confidence=council_verdict.confidence,
            verdict_summary=council_verdict.summary,
            category=category
        )
        
        return {
            "claim": claim,
            "verdict": final_verdict,
            "confidence": council_verdict.confidence,
            "truth_probability": council_verdict.confidence * 100 if final_verdict == "TRUE" else (1 - council_verdict.confidence) * 100,
            "summary": council_verdict.summary,
            "council_vote": council_verdict.vote_breakdown,
            "market_id": market.market_id,
            "processing_time": f"{processing_time:.1f}s"
        }
        
    except Exception as e:
        logger.error(f"Verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MARKET ENDPOINTS ====================

@app.get("/market/list")
def list_markets(
    category: Optional[str] = None,
    status: Optional[str] = "open",
    limit: int = Query(default=20, le=100)
):
    """List markets with optional filtering."""
    if category:
        markets = market_manager.get_markets_by_category(category)
    else:
        markets = market_manager.get_open_markets()
    
    return {
        "markets": [m.to_dict() for m in markets[:limit]],
        "total": len(markets)
    }


@app.get("/market/hot")
def get_hot_markets(limit: int = Query(default=10, le=50)):
    """Get markets with highest volume."""
    markets = market_manager.get_hot_markets(limit)
    return {"markets": [m.to_dict() for m in markets]}


@app.get("/market/ending-soon")
def get_ending_soon(limit: int = Query(default=10, le=50)):
    """Get markets ending soon."""
    markets = market_manager.get_ending_soon(limit)
    return {"markets": [m.to_dict() for m in markets]}


@app.get("/market/{market_id}")
def get_market(market_id: str):
    """Get single market details."""
    market = market_manager.get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    bets = market_manager.get_market_bets(market_id)
    return {
        "market": market.to_dict(),
        "bets_count": len(bets),
        "recent_bets": [b.to_dict() for b in bets[-5:]]
    }


@app.post("/market/bet")
def place_bet(request: BetRequest):
    """Place a bet on a market."""
    try:
        position = BetPosition(request.position)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid position. Use 'correct' or 'wrong'")
    
    bet, message = market_manager.place_bet(
        user_id=request.user_id,
        market_id=request.market_id,
        position=position,
        amount=request.amount
    )
    
    if not bet:
        raise HTTPException(status_code=400, detail=message)
    
    # Get updated market
    market = market_manager.get_market(request.market_id)
    
    return {
        "success": True,
        "message": message,
        "bet": bet.to_dict(),
        "market": market.to_dict() if market else None
    }


@app.post("/market/resolve")
def resolve_market(request: ResolveRequest):
    """Resolve a market (admin only in production)."""
    try:
        outcome = ResolutionOutcome(request.outcome)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid outcome")
    
    success, message, payouts = market_manager.resolve_market(
        market_id=request.market_id,
        outcome=outcome,
        resolution_source=request.source,
        resolution_evidence=request.evidence
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "payouts": payouts
    }


# ==================== USER ENDPOINTS ====================

@app.post("/user/create")
def create_user(request: UserRequest):
    """Create a new user with initial tokens."""
    user = market_manager.create_user(request.username)
    return {"user": user.to_dict()}


@app.get("/user/{user_id}")
def get_user(user_id: str):
    """Get user details and stats."""
    stats = market_manager.get_user_stats(user_id)
    if not stats:
        raise HTTPException(status_code=404, detail="User not found")
    return stats


@app.get("/user/{user_id}/bets")
def get_user_bets(user_id: str, status: Optional[str] = None):
    """Get user's bets."""
    if status == "active":
        bets = market_manager.get_user_active_bets(user_id)
    else:
        bets = market_manager.get_user_bets(user_id)
    
    return {"bets": [b.to_dict() for b in bets]}


@app.post("/user/{user_id}/tokens")
def add_tokens(user_id: str, amount: float = Query(...)):
    """Add tokens to user (for testing)."""
    success = market_manager.add_tokens(user_id, amount)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = market_manager.get_user(user_id)
    return {"success": True, "new_balance": user.balance if user else 0}


# ==================== LEADERBOARD ====================

@app.get("/leaderboard")
def get_leaderboard(limit: int = Query(default=10, le=100)):
    """Get top users by profit."""
    leaderboard = market_manager.get_leaderboard(limit)
    return {"leaderboard": [e.to_dict() for e in leaderboard]}


# ==================== STATS ====================

@app.get("/stats")
def get_platform_stats():
    """Get overall platform statistics."""
    return market_manager.get_platform_stats()
