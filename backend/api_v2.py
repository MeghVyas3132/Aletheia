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

SECURITY:
- CORS restricted to allowed origins
- Rate limiting on verification endpoints
- Input sanitization and length limits
- Admin authentication for market resolution
"""

import os
import re
import logging
import asyncio
import json
import time
import hashlib
from typing import Optional
from datetime import datetime
from functools import wraps

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Header, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# Agents - Use fast triage
from agents import (
    FactChecker, ForensicExpert, TheJudge,
    DomainAgentRegistry, Domain,
    DevilsAdvocate, AICouncil, Vote,
    ReportGenerator, ClaimProcessor,
    QuestionAnswerer, get_question_answerer
)
from agents.claim_triage_fast import FastClaimTriage, get_fast_triage, Complexity, InputType

# Market
from market import (
    TruthMarketManager, get_market_manager,
    Market, Bet, BetPosition, ResolutionOutcome, MarketStatus
)

# DOW (Decentralized Oracle of Wisdom)
from dow import (
    DOWManager, get_dow_manager,
    Challenge, ChallengeStatus, Vote as DOWVote
)

# Anti-sybil protection
from dow.anti_sybil import get_anti_sybil_checker

# Background scheduler
from scheduler import setup_scheduler, shutdown_scheduler

# Verification history
from verification_history import (
    get_history_db, create_verification_record,
    VerificationRecord, VerificationHistoryDB
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Aletheia-API-V2")

# ==================== SECURITY CONFIG ====================

# Allowed CORS origins (add your production domains)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "https://aletheia-rczr.onrender.com",  # Render frontend
    "https://aletheia-frontend.vercel.app",  # Vercel frontend (add your actual domain)
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
]

# Allow all origins if CORS_ALLOW_ALL is set (for development/testing)
if os.getenv("CORS_ALLOW_ALL", "").lower() == "true":
    ALLOWED_ORIGINS = ["*"]

# Admin API key for protected endpoints
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "aletheia-admin-key-change-in-prod")

# Rate limiting config
RATE_LIMIT_REQUESTS = 30  # requests per minute
rate_limit_store: dict = {}  # Simple in-memory rate limiting

# Input limits
MAX_CLAIM_LENGTH = 2000
MIN_CLAIM_LENGTH = 3

# ==================== SECURITY HELPERS ====================

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent prompt injection.
    Removes potentially dangerous patterns while preserving meaning.
    """
    if not text:
        return ""
    
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove potential prompt injection patterns
    dangerous_patterns = [
        r'ignore\s+(previous|above|all)\s+instructions?',
        r'disregard\s+(previous|above|all)',
        r'forget\s+(everything|all|previous)',
        r'you\s+are\s+now\s+',
        r'new\s+instructions?:',
        r'system\s*:',
        r'<\|.*?\|>',  # Special tokens
        r'\[INST\]',
        r'\[/INST\]',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()


def check_rate_limit(client_ip: str) -> bool:
    """Simple rate limiting check."""
    now = time.time()
    minute_ago = now - 60
    
    # Clean old entries
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store.get(client_ip, [])
        if t > minute_ago
    ]
    
    # Check limit
    if len(rate_limit_store.get(client_ip, [])) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Record request
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    rate_limit_store[client_ip].append(now)
    
    return True


def verify_admin_key(x_admin_key: str = Header(None)) -> bool:
    """Verify admin API key for protected endpoints."""
    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing admin API key"
        )
    return True


# ==================== LIFESPAN (Startup/Shutdown) ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Aletheia API V2...")
    
    # Start background scheduler
    await setup_scheduler()
    logger.info("Background scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Aletheia API V2...")
    await shutdown_scheduler()
    logger.info("Background scheduler stopped")


# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Aletheia API V2",
    description="AI-Powered Fact-Checking with Truth Market",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - Restricted to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
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
question_answerer = get_question_answerer()  # NEW: For questions, not claims

# Market manager
market_manager = get_market_manager()


# ==================== REQUEST MODELS (with validation) ====================

class ClaimRequest(BaseModel):
    claim: str = Field(..., min_length=MIN_CLAIM_LENGTH, max_length=MAX_CLAIM_LENGTH)
    
    @field_validator('claim')
    @classmethod
    def validate_claim(cls, v: str) -> str:
        """Validate and sanitize claim input."""
        if not v or not v.strip():
            raise ValueError("Claim cannot be empty")
        
        sanitized = sanitize_input(v)
        
        if len(sanitized) < MIN_CLAIM_LENGTH:
            raise ValueError(f"Claim too short (min {MIN_CLAIM_LENGTH} chars)")
        if len(sanitized) > MAX_CLAIM_LENGTH:
            raise ValueError(f"Claim too long (max {MAX_CLAIM_LENGTH} chars)")
        
        return sanitized


class BetRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    market_id: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., pattern="^(correct|wrong)$")
    amount: float = Field(..., gt=0, le=10000)  # Must be positive, max 10k
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate bet amount."""
        if v <= 0:
            raise ValueError("Bet amount must be positive")
        if v > 10000:
            raise ValueError("Maximum bet is 10,000 ALETH")
        return round(v, 2)  # Round to 2 decimal places


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
            "Truth Market betting",
            "Decentralized Oracle of Wisdom (DOW)",
            "Anti-sybil protection"
        ]
    }


@app.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status.
    Use this for monitoring and debugging.
    """
    components = {}
    overall_healthy = True
    
    # Check LLM (Groq) connectivity
    try:
        # Quick test that doesn't use tokens
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile")
        components["llm_groq"] = {"status": "configured", "model": "llama-3.3-70b-versatile"}
    except Exception as e:
        components["llm_groq"] = {"status": "error", "error": str(e)}
        overall_healthy = False
    
    # Check DOW manager
    try:
        treasury = dow_manager.get_treasury_stats()
        active_challenges = dow_manager.get_active_challenges()
        components["dow"] = {
            "status": "healthy",
            "treasury_balance": treasury.get("balance", 0),
            "active_challenges": len(active_challenges)
        }
    except Exception as e:
        components["dow"] = {"status": "error", "error": str(e)}
        overall_healthy = False
    
    # Check Market manager
    try:
        from market import get_market_manager
        mm = get_market_manager()
        open_markets = len(mm.get_open_markets())
        components["market"] = {
            "status": "healthy",
            "open_markets": open_markets
        }
    except Exception as e:
        components["market"] = {"status": "error", "error": str(e)}
    
    # Check Anti-sybil
    try:
        components["anti_sybil"] = {
            "status": "healthy",
            "demo_mode": anti_sybil_checker.config.demo_mode,
            "strict_mode": anti_sybil_checker.config.strict_mode
        }
    except Exception as e:
        components["anti_sybil"] = {"status": "error", "error": str(e)}
    
    # Check scheduler
    try:
        from scheduler import get_scheduler
        scheduler = get_scheduler()
        components["scheduler"] = {
            "status": "healthy" if scheduler.running else "stopped",
            "tasks": list(scheduler.tasks.keys())
        }
    except Exception as e:
        components["scheduler"] = {"status": "error", "error": str(e)}
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": components
    }


@app.get("/health/agents")
def agents_health_check():
    """Check status of AI agents."""
    agents_status = {
        "fact_checker": "ready" if fact_checker else "not_initialized",
        "forensic_expert": "ready" if forensic_expert else "not_initialized",
        "devils_advocate": "ready" if devils_advocate else "not_initialized",
        "ai_council": "ready" if ai_council else "not_initialized",
        "judge": "ready" if judge else "not_initialized",
        "fast_triage": "ready" if fast_triage else "not_initialized",
        "question_answerer": "ready" if question_answerer else "not_initialized"
    }
    
    return {
        "status": "healthy" if all(v == "ready" for v in agents_status.values()) else "degraded",
        "agents": agents_status
    }


# ==================== VERIFICATION ENDPOINTS ====================

@app.post("/verify_stream")
async def verify_claim_stream(request: ClaimRequest, req: Request):
    """
    Full verification with streaming updates.
    Shows progress of each agent and council debate.
    """
    # Rate limiting check
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")

    start_time = time.time()

    async def event_generator():
        try:
            # Phase 1: Fast Triage (rule-based, NO LLM)
            yield f"data: {json.dumps({'type': 'status', 'phase': 'triage', 'message': 'Analyzing input...'})}\n\n"
            
            triage_result = fast_triage.triage(claim)
            
            yield f"data: {json.dumps({'type': 'triage', 'data': {'domains': [d.value for d in triage_result.domains], 'complexity': triage_result.complexity.value, 'entities': triage_result.entities, 'claim_type': triage_result.claim_type, 'input_type': triage_result.input_type.value}})}\n\n"
            
            # Check if this is a QUESTION (not a claim to verify)
            if triage_result.input_type in (InputType.QUESTION, InputType.COMPARISON):
                # Use Question Answerer instead of verification pipeline
                yield f"data: {json.dumps({'type': 'status', 'phase': 'research', 'message': 'This is a question - researching answer...'})}\n\n"
                
                # Quick research via fact checker for sources
                a1_result = {}
                async for event in fact_checker.astream_verify(claim):
                    for node, state in event.items():
                        if node == "analyst" and "evidence_dossier" in state:
                            a1_result = state["evidence_dossier"]
                
                search_results = a1_result.get("search_results", [])
                
                yield f"data: {json.dumps({'type': 'status', 'phase': 'answering', 'message': 'Generating answer with sources...'})}\n\n"
                
                # Get answer from Question Answerer
                answer_result = await question_answerer.answer(claim, search_results)
                
                processing_time = time.time() - start_time
                
                # Send answer result (different format from verification)
                final_result = {
                    "type": "answer",  # Not "result" - this is an ANSWER
                    "input_type": triage_result.input_type.value,
                    "question": claim,
                    "answer": answer_result.answer,
                    "summary": answer_result.summary,
                    "nuance": answer_result.nuance,
                    "is_contentious": answer_result.is_contentious,
                    "sources": answer_result.sources[:5],
                    "confidence": answer_result.confidence,
                    "domains": [d.value for d in triage_result.domains],
                    "processing_time": round(processing_time, 2)
                }
                
                yield f"data: {json.dumps(final_result)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # ========== CLAIM VERIFICATION PIPELINE (for statements, not questions) ==========
            
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
            # Flatten search results from evidence_dossier (same as non-streaming endpoint)
            flat_sources = []
            for query_result in a1_result.get("search_results", []):
                if isinstance(query_result, dict):
                    for source in query_result.get("results", []):
                        flat_sources.append(source)
            
            # Add domain evidence
            all_sources = flat_sources + domain_evidence
            
            # Debug log
            logger.info(f"[Stream] Found {len(flat_sources)} sources for claim: {claim[:50]}...")
            for i, src in enumerate(flat_sources[:3]):
                logger.info(f"  [Stream] Source {i+1}: {src.get('title', 'N/A')[:80]}")
            
            # Phase 4: Devil's Advocate
            yield f"data: {json.dumps({'type': 'status', 'phase': 'devils_advocate', 'message': 'Devils Advocate challenging the claim...'})}\n\n"
            
            counter_evidence = await devils_advocate.challenge(
                claim=claim,
                supporting_evidence=all_sources,
                entities=triage_result.entities
            )
            
            yield f"data: {json.dumps({'type': 'devils_advocate', 'attack_strength': counter_evidence.overall_attack_strength, 'counter_arguments': [arg.argument for arg in counter_evidence.counter_arguments[:2]], 'recommendation': counter_evidence.recommendation})}\n\n"
            
            # Phase 5: AI Council Debate
            yield f"data: {json.dumps({'type': 'status', 'phase': 'council', 'message': 'AI Council convening for debate...'})}\n\n"
            
            supporting_evidence = {
                "sources": all_sources,
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
            for debate_round in council_verdict.debate_transcript:
                yield f"data: {json.dumps({'type': 'debate_round', 'round': debate_round.round_num, 'round_type': debate_round.round_type, 'prosecutor': debate_round.prosecutor_argument.argument[:200], 'defender': debate_round.defender_argument.argument[:200]})}\n\n"
            
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
            
            # Save to verification history
            try:
                verification_record = create_verification_record(
                    claim=claim,
                    verdict=final_verdict,
                    confidence=council_verdict.confidence,
                    domain=triage_result.domains[0].value if triage_result.domains else "general",
                    complexity=triage_result.complexity.value,
                    council_vote=council_verdict.vote_breakdown,
                    sources=[s.get("url", "") for s in a1_result.get("search_results", [])[:5]],
                    explanation=council_verdict.summary,
                    nuance=getattr(council_verdict, 'nuance', ''),
                    verification_time=processing_time,
                    user_ip=client_ip
                )
                history_db.save(verification_record)
                complete_result["verification_id"] = verification_record.id
            except Exception as hist_error:
                logger.warning(f"Failed to save verification history: {hist_error}")
            
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
async def verify_claim(request: ClaimRequest, req: Request):
    """
    Non-streaming verification endpoint.
    Returns complete result after all processing.
    """
    # Rate limiting check
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
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
        
        # Flatten search results for AI Council
        # a1_result["search_results"] is a list of query results: [{"query": ..., "results": [...]}]
        # We need to extract the actual source objects
        flat_sources = []
        for query_result in a1_result.get("search_results", []):
            if isinstance(query_result, dict):
                for source in query_result.get("results", []):
                    flat_sources.append(source)
        
        # Combine with domain evidence
        domain_evidence = []
        for dr in domain_results:
            domain_evidence.extend(dr.evidence)
        
        all_sources = flat_sources + domain_evidence
        
        # Debug log - show source content
        logger.info(f"Fact checker found {len(flat_sources)} sources for claim: {claim[:50]}...")
        for i, src in enumerate(flat_sources[:3]):
            logger.info(f"  Source {i+1}: {src.get('title', 'N/A')[:80]}")
            logger.info(f"    Content: {src.get('content', '')[:200]}")
        
        # Devil's Advocate
        counter_evidence = await devils_advocate.challenge(
            claim=claim,
            supporting_evidence=all_sources,
            entities=triage_result.entities
        )
        
        # AI Council
        supporting_evidence = {
            "sources": all_sources,
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
def resolve_market(
    request: ResolveRequest,
    admin_verified: bool = Depends(verify_admin_key)
):
    """Resolve a market (admin only - requires X-Admin-Key header)."""
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


# ==================== DOW (Decentralized Oracle of Wisdom) ====================

dow_manager = get_dow_manager()


# Request models for DOW
class ChallengeSubmitRequest(BaseModel):
    verdict_id: str = Field(..., min_length=1)
    challenger_wallet: str = Field(..., min_length=1)
    stake_amount: float = Field(..., gt=0, le=100)
    evidence_links: list[str] = Field(..., min_length=2)
    explanation: str = Field(..., min_length=100)


class VoteRequest(BaseModel):
    voter_wallet: str = Field(..., min_length=1)
    position: str = Field(..., pattern="^(ai|challenger)$")
    reasoning: Optional[str] = None


class ForceResolveRequest(BaseModel):
    winner: str = Field(..., pattern="^(ai|challenger)$")
    reason: str = Field(..., min_length=10)


# Challenge endpoints
@app.post("/challenge/submit")
def submit_challenge(request: ChallengeSubmitRequest):
    """
    Submit a challenge to a verdict.
    
    Requires:
    - verdict_id: ID of the verdict to challenge
    - challenger_wallet: Wallet address of challenger
    - stake_amount: SOL to stake (1-100)
    - evidence_links: At least 2 evidence URLs
    - explanation: At least 100 chars explaining why verdict is wrong
    """
    success, message, challenge = dow_manager.submit_challenge(
        verdict_id=request.verdict_id,
        challenger_wallet=request.challenger_wallet,
        stake_amount=request.stake_amount,
        evidence_links=request.evidence_links,
        explanation=request.explanation
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "challenge": challenge.to_dict()
    }


@app.get("/challenge/{challenge_id}")
def get_challenge(challenge_id: str):
    """Get challenge details."""
    challenge = dow_manager.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    return {"challenge": challenge.to_dict()}


@app.get("/challenges/active")
def get_active_challenges():
    """Get all active challenges (voting in progress)."""
    challenges = dow_manager.get_active_challenges()
    return {
        "count": len(challenges),
        "challenges": [c.to_dict() for c in challenges]
    }


@app.get("/challenges/wallet/{wallet_address}")
def get_challenges_by_wallet(wallet_address: str):
    """Get all challenges submitted by a wallet."""
    challenges = dow_manager.get_challenges_by_wallet(wallet_address)
    return {
        "count": len(challenges),
        "challenges": [c.to_dict() for c in challenges]
    }


# Voting endpoints
# Anti-sybil checker instance
anti_sybil_checker = get_anti_sybil_checker()


@app.post("/challenge/{challenge_id}/vote")
async def cast_vote(challenge_id: str, request: VoteRequest):
    """
    Cast a vote on a challenge.
    
    Requires:
    - voter_wallet: Wallet address of voter
    - position: "ai" (AI is correct) or "challenger" (challenger is correct)
    - reasoning: Optional explanation for vote
    
    Anti-sybil protections:
    - Wallet age check (min 7 days)
    - SOL balance check (min 0.1 SOL)
    - Transaction history check (min 5 transactions)
    - Rate limiting (max 10 votes/hour)
    """
    # Check anti-sybil eligibility
    try:
        is_eligible, reason = await anti_sybil_checker.is_eligible_to_vote(
            wallet_address=request.voter_wallet,
            challenge_id=challenge_id
        )
        
        if not is_eligible:
            raise HTTPException(
                status_code=403,
                detail=f"Vote rejected: {reason}"
            )
    except Exception as e:
        # Log error but allow vote if anti-sybil check fails
        # (graceful degradation - don't block voting if Solana RPC is down)
        logger.warning(f"Anti-sybil check failed for {request.voter_wallet}: {e}")
    
    success, message, vote = dow_manager.cast_vote(
        challenge_id=challenge_id,
        voter_wallet=request.voter_wallet,
        position=request.position,
        reasoning=request.reasoning
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "vote": vote.to_dict()
    }


@app.get("/challenge/{challenge_id}/votes")
def get_challenge_votes(challenge_id: str):
    """Get all votes for a challenge."""
    challenge = dow_manager.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    votes = dow_manager.get_votes_for_challenge(challenge_id)
    
    return {
        "challenge_id": challenge_id,
        "votes_for_ai": challenge.votes_for_ai,
        "votes_for_challenger": challenge.votes_for_challenger,
        "voter_count": challenge.voter_count,
        "ai_percentage": challenge.ai_vote_percentage,
        "challenger_percentage": challenge.challenger_vote_percentage,
        "votes": [v.to_dict() for v in votes]
    }


@app.get("/voter/{wallet_address}/eligibility")
async def check_vote_eligibility(wallet_address: str, challenge_id: Optional[str] = None):
    """
    Check if a wallet is eligible to vote.
    
    Returns eligibility status and reasons if not eligible.
    Call this before allowing users to vote in the UI.
    """
    try:
        is_eligible, reason = await anti_sybil_checker.is_eligible_to_vote(
            wallet_address=wallet_address,
            challenge_id=challenge_id
        )
        
        return {
            "wallet": wallet_address,
            "eligible": is_eligible,
            "reason": reason if not is_eligible else "Wallet meets all requirements",
            "requirements": {
                "min_wallet_age_days": anti_sybil_checker.config.min_wallet_age_days,
                "min_sol_balance": anti_sybil_checker.config.min_sol_balance,
                "min_transaction_count": anti_sybil_checker.config.min_transaction_count,
                "max_votes_per_hour": anti_sybil_checker.config.max_votes_per_hour
            }
        }
    except Exception as e:
        logger.error(f"Eligibility check failed: {e}")
        return {
            "wallet": wallet_address,
            "eligible": True,  # Graceful degradation
            "reason": "Unable to verify - allowing vote",
            "warning": "Anti-sybil check unavailable"
        }


# Resolution endpoints
@app.post("/challenge/resolve-pending")
def resolve_pending_challenges():
    """
    Check and resolve all challenges whose voting period has ended.
    This should be called periodically (e.g., via cron job).
    """
    resolved = dow_manager.check_and_resolve_challenges()
    return {
        "resolved_count": len(resolved),
        "results": [{"challenge_id": cid, "outcome": outcome} for cid, outcome in resolved]
    }


@app.post("/challenge/{challenge_id}/force-resolve")
def force_resolve_challenge(
    challenge_id: str,
    request: ForceResolveRequest,
    admin_verified: bool = Depends(verify_admin_key)
):
    """
    Admin force-resolve a challenge.
    Requires X-Admin-Key header.
    """
    success, message = dow_manager.force_resolve(
        challenge_id=challenge_id,
        winner=request.winner,
        reason=request.reason
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


# Treasury endpoints
@app.get("/treasury")
def get_treasury_stats():
    """Get Aletheia treasury statistics."""
    return dow_manager.get_treasury_stats()


@app.post("/treasury/fund")
def fund_treasury(
    amount: float = Query(..., gt=0),
    admin_verified: bool = Depends(verify_admin_key)
):
    """Add funds to treasury (admin only)."""
    dow_manager.add_treasury_funds(amount)
    return {
        "success": True,
        "message": f"Added {amount} SOL to treasury",
        "treasury": dow_manager.get_treasury_stats()
    }


# Voter endpoints
@app.get("/voter/{wallet_address}")
def get_voter_info(wallet_address: str):
    """Get voter information and stats."""
    voter = dow_manager.get_or_create_voter(wallet_address)
    return {"voter": voter.to_dict()}


@app.get("/voter/{wallet_address}/reputation")
def get_voter_reputation(wallet_address: str):
    """Get voter reputation score."""
    voter = dow_manager.get_or_create_voter(wallet_address)
    return {
        "wallet": wallet_address,
        "reputation": voter.reputation,
        "accuracy": round(voter.historical_accuracy * 100, 1),
        "total_votes": voter.total_votes,
        "vote_weight": voter.calculate_vote_weight()
    }


# DOW Leaderboards
@app.get("/dow/leaderboard/challengers")
def get_challenger_leaderboard(limit: int = Query(default=10, le=50)):
    """Get top challengers by successful challenges."""
    leaderboard = dow_manager.get_challenger_leaderboard(limit)
    return {"leaderboard": leaderboard}


@app.get("/dow/leaderboard/voters")
def get_voter_leaderboard(limit: int = Query(default=10, le=50)):
    """Get top voters by accuracy and reputation."""
    leaderboard = dow_manager.get_voter_leaderboard(limit)
    return {"leaderboard": leaderboard}


# Verdict registration (called internally after verification)
@app.post("/verdict/register")
def register_verdict(
    verdict_id: str,
    claim: str,
    domain: str,
    verdict: str,
    confidence: float
):
    """
    Register a verdict for potential challenges.
    Called internally after verification completes.
    """
    dow_manager.register_verdict(
        verdict_id=verdict_id,
        claim=claim,
        domain=domain,
        verdict=verdict,
        confidence=confidence
    )
    
    return {
        "success": True,
        "verdict_id": verdict_id,
        "challengeable": True,
        "challenge_window_hours": dow_manager.config.challenge_window
    }


@app.get("/verdict/{verdict_id}/challengeable")
def check_verdict_challengeable(verdict_id: str):
    """Check if a verdict can be challenged."""
    can_challenge, reason = dow_manager.is_verdict_challengeable(verdict_id)
    verdict_info = dow_manager.get_verdict(verdict_id)
    
    return {
        "verdict_id": verdict_id,
        "challengeable": can_challenge,
        "reason": reason,
        "verdict_info": verdict_info
    }


# ==================== VERIFICATION HISTORY ====================

history_db = get_history_db()


@app.get("/history/recent")
def get_recent_verifications(limit: int = Query(default=20, le=100)):
    """Get recent public verifications."""
    verifications = history_db.get_recent(limit)
    return {
        "count": len(verifications),
        "verifications": [v.to_dict() for v in verifications]
    }


@app.get("/history/search")
def search_verifications(
    q: str = Query(..., min_length=3, description="Search query"),
    verdict: Optional[str] = Query(None, pattern="^(TRUE|FALSE|UNCERTAIN)$"),
    limit: int = Query(default=20, le=100)
):
    """Search past verifications by claim text."""
    verifications = history_db.search(query=q, verdict=verdict, limit=limit)
    return {
        "query": q,
        "verdict_filter": verdict,
        "count": len(verifications),
        "verifications": [v.to_dict() for v in verifications]
    }


@app.get("/history/{verification_id}")
def get_verification(verification_id: str):
    """Get a specific verification by ID."""
    record = history_db.get(verification_id)
    if not record:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    return {"verification": record.to_dict()}


@app.get("/history/wallet/{wallet_address}")
def get_wallet_history(
    wallet_address: str,
    limit: int = Query(default=50, le=100)
):
    """Get verification history for a wallet."""
    verifications = history_db.get_by_wallet(wallet_address, limit)
    return {
        "wallet": wallet_address,
        "count": len(verifications),
        "verifications": [v.to_dict() for v in verifications]
    }


@app.get("/history/stats")
def get_verification_stats():
    """Get verification statistics and analytics."""
    stats = history_db.get_stats()
    return {"stats": stats}


@app.get("/history/similar")
def find_similar_verification(
    claim: str = Query(..., min_length=10),
    hours: int = Query(default=24, le=168)
):
    """
    Find if a similar claim was verified recently.
    Useful for caching and avoiding duplicate verifications.
    """
    similar = history_db.find_similar(claim, threshold_hours=hours)
    
    if similar:
        return {
            "found": True,
            "verification": similar.to_dict(),
            "message": f"Similar claim was verified {similar.created_at}"
        }
    
    return {
        "found": False,
        "message": f"No similar verification found in the last {hours} hours"
    }

