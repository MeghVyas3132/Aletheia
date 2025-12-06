# 🛡️ Aletheia - Complete System Architecture & Documentation

> **Aletheia** (Ancient Greek: ἀλήθεια) means "truth" or "disclosure" — the philosophical concept of revealing what is hidden.

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Technology Stack](#3-technology-stack)
4. [Architecture Deep Dive](#4-architecture-deep-dive)
5. [Agent System](#5-agent-system)
6. [Verification Pipeline](#6-verification-pipeline)
7. [Question vs Claim Detection](#7-question-vs-claim-detection)
8. [AI Council Debate System](#8-ai-council-debate-system)
9. [Truth Market (Prediction Market)](#9-truth-market-prediction-market)
10. [Frontend Architecture](#10-frontend-architecture)
11. [API Reference](#11-api-reference)
12. [Security Implementation](#12-security-implementation)
13. [Data Flow Diagrams](#13-data-flow-diagrams)
14. [Deployment Architecture](#14-deployment-architecture)
15. [Future Roadmap](#15-future-roadmap)

---

## 1. Executive Summary

**Aletheia** is an AI-powered fact-checking platform that combines:

- **Multi-Agent Verification**: 6+ specialized AI agents that investigate claims from different perspectives
- **Adversarial Debate**: An AI Council with Prosecutor, Defender, and Jury that debates each claim
- **Prediction Market**: Users can bet on whether Aletheia's verdicts are correct (Polymarket-style)
- **Question Answering**: Intelligently detects questions vs claims and provides appropriate responses

### Key Innovation

Unlike traditional fact-checkers that just return TRUE/FALSE, Aletheia uses an **adversarial multi-agent debate system** where AI agents argue BOTH sides of a claim before a jury votes on the verdict. This mimics a courtroom trial to reduce bias and increase accuracy.

### Core Metrics
- **LLM Provider**: Groq (Llama 3.1 8B Instant) - ~200ms response times
- **Search Engine**: Tavily API for real-time web search
- **Triage**: 0 LLM calls (pure regex/keyword matching)
- **Full Verification**: 8-15 LLM calls depending on complexity
- **End-to-End Latency**: 15-45 seconds per claim

---

## 2. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ALETHEIA SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐        │
│  │    Frontend     │────▶│    Backend      │────▶│   External      │        │
│  │   (Next.js)     │◀────│   (FastAPI)     │◀────│   Services      │        │
│  │   Port: 3000    │     │   Port: 8000    │     │                 │        │
│  └─────────────────┘     └─────────────────┘     │  • Groq LLM     │        │
│         │                       │                 │  • Tavily Search│        │
│         │                       │                 │                 │        │
│         ▼                       ▼                 └─────────────────┘        │
│  ┌─────────────────┐     ┌─────────────────┐                                 │
│  │   User Input    │     │  Agent System   │                                 │
│  │   • Claims      │     │  • 6+ Agents    │                                 │
│  │   • Questions   │     │  • AI Council   │                                 │
│  │   • Bets        │     │  • Truth Market │                                 │
│  └─────────────────┘     └─────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### High-Level Flow

1. **User submits input** (claim or question) via web interface
2. **Fast Triage** classifies input type (question/claim) and determines complexity
3. **Route Decision**:
   - If **QUESTION** → QuestionAnswerer agent provides factual answer
   - If **CLAIM** → Full verification pipeline with AI Council debate
4. **Streaming Response** sends real-time updates to frontend
5. **Market Creation** (optional) creates betting market for the claim
6. **Result Display** shows verdict, confidence, sources, and debate transcript

---

## 3. Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | FastAPI 0.122+ | Async REST API with automatic OpenAPI docs |
| **LLM Orchestration** | LangChain 0.3 + LangGraph 0.2 | Agent workflows and state machines |
| **LLM Provider** | Groq (Llama 3.1 8B Instant) | Ultra-fast inference (~200ms/call) |
| **Web Search** | Tavily API | Real-time search with source extraction |
| **Data Validation** | Pydantic 2.12 | Request/response validation |
| **PDF Generation** | ReportLab | Generate verification reports |
| **Runtime** | Python 3.12 | Modern async/await support |

### Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | Next.js 16 | React-based with App Router |
| **UI Library** | React 19 | Latest concurrent features |
| **Styling** | Tailwind CSS 4 | Utility-first CSS |
| **Animations** | Framer Motion | Smooth UI transitions |
| **Icons** | Lucide React | Modern icon set |
| **Theme** | next-themes | Dark/light mode support |
| **Type Safety** | TypeScript 5 | Full type coverage |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker + Docker Compose | Consistent deployment |
| **Backend Container** | Python 3.12-slim | Minimal image size |
| **Frontend Container** | Node.js Alpine | Production build |
| **Network** | Docker bridge network | Inter-container communication |

### External APIs

| Service | Purpose | Rate Limits |
|---------|---------|-------------|
| **Groq API** | LLM inference | 30 req/min (free tier) |
| **Tavily API** | Web search | 1000 req/month (free tier) |

---

## 4. Architecture Deep Dive

### 4.1 Backend Structure

```
backend/
├── api_v2.py              # Main FastAPI application (752 lines)
├── main.py                # CLI interface with Rich UI
├── pyproject.toml         # Python dependencies
├── Dockerfile             # Backend container config
│
├── agents/                # AI Agent System
│   ├── __init__.py        # Agent exports
│   ├── claim_triage_fast.py    # Rule-based input classification
│   ├── fact_checker.py         # Web search & evidence gathering
│   ├── forensic_expert.py      # Linguistic & source analysis
│   ├── judge.py                # Final verdict synthesis
│   ├── devils_advocate.py      # Counter-argument generation
│   ├── ai_council.py           # Prosecutor/Defender/Jury debate
│   ├── domain_registry.py      # Domain-specific agents
│   ├── question_answerer.py    # Question answering (not verification)
│   ├── claim_processor.py      # Claim caching & processing
│   └── shelby.py               # PDF report generation
│
├── market/                # Prediction Market System
│   ├── __init__.py        # Market exports
│   ├── models.py          # Market, Bet, User data models
│   └── manager.py         # Market operations
│
├── storage/               # Generated reports (PDF)
│
└── move_smart_contract/   # (Legacy) Aptos blockchain integration
```

### 4.2 Frontend Structure

```
frontend/
├── package.json           # Node.js dependencies
├── next.config.ts         # Next.js configuration
├── Dockerfile             # Frontend container config
│
├── app/                   # Next.js App Router
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main verification page
│   ├── globals.css        # Global styles + Tailwind
│   └── about/
│       └── page.tsx       # Team information
│
├── components/            # React Components
│   ├── Navbar.tsx         # Navigation bar
│   ├── SearchHero.tsx     # Main search input
│   ├── VerificationProgress.tsx  # Real-time logs
│   ├── VerificationResult.tsx    # Verdict display
│   ├── mode-toggle.tsx    # Dark/light theme toggle
│   └── theme-provider.tsx # Theme context
│
└── public/                # Static assets
```

---

## 5. Agent System

Aletheia uses a **multi-agent architecture** where each agent has a specialized role:

### 5.1 Agent Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT PIPELINE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐                                                  │
│  │ FastClaimTriage│  ← Rule-based (0 LLM calls)                     │
│  │  • Input type  │                                                 │
│  │  • Domains     │                                                 │
│  │  • Complexity  │                                                 │
│  └───────┬───────┘                                                  │
│          │                                                          │
│    ┌─────┴─────┐                                                    │
│    │  QUESTION  │──────────▶ QuestionAnswerer                       │
│    └───────────┘                   │                                │
│          │                         ▼                                │
│    ┌─────┴─────┐            ┌─────────────┐                         │
│    │   CLAIM   │            │   Answer    │                         │
│    └───────────┘            │   Result    │                         │
│          │                  └─────────────┘                         │
│          ▼                                                          │
│  ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     │
│  │  FactChecker  │────▶│ForensicExpert │────▶│Devil'sAdvocate│     │
│  │  (3 agents)   │     │  (Linguist)   │     │  (Challenger) │     │
│  └───────────────┘     └───────────────┘     └───────────────┘     │
│          │                    │                     │               │
│          └────────────────────┼─────────────────────┘               │
│                               ▼                                     │
│                    ┌───────────────────┐                            │
│                    │    AI COUNCIL     │                            │
│                    │ ┌───────────────┐ │                            │
│                    │ │  Prosecutor   │ │ ← Argues claim is FALSE    │
│                    │ │  Defender     │ │ ← Argues claim is TRUE     │
│                    │ │  Jury (3)     │ │ ← Votes on verdict         │
│                    │ └───────────────┘ │                            │
│                    └─────────┬─────────┘                            │
│                              ▼                                      │
│                    ┌───────────────────┐                            │
│                    │    TheJudge       │  ← Final synthesis         │
│                    └───────────────────┘                            │
│                              │                                      │
│                              ▼                                      │
│                    ┌───────────────────┐                            │
│                    │  FINAL VERDICT    │                            │
│                    │  TRUE/FALSE/      │                            │
│                    │  UNCERTAIN        │                            │
│                    └───────────────────┘                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Individual Agent Details

#### FastClaimTriage (Rule-Based, 0 LLM Calls)

**File**: `agents/claim_triage_fast.py`

**Purpose**: Classify user input without using expensive LLM calls

**Key Logic**:
```python
class InputType(Enum):
    CLAIM = "claim"        # Statement to verify → TRUE/FALSE
    QUESTION = "question"  # Question to answer → Provide answer
    COMPARISON = "comparison"  # Comparing things → Analysis

# Detection patterns
QUESTION_PATTERNS = [
    r'^(who|what|where|when|why|how|which|whose|whom)\s',
    r'^(is|are|was|were|do|does|did|can|could|will|would|should)\s',
    r'\?$',
]

COMPARISON_PATTERNS = [
    r'\b(or)\b.*\?',  # "X or Y?"
    r'\b(vs|versus|compared to|better than)\b',
]
```

**Output**:
```python
@dataclass
class TriageResult:
    original_claim: str
    normalized_claim: str
    domains: List[Domain]      # [TECH, FINANCE, ...]
    complexity: Complexity     # SIMPLE, MEDIUM, COMPLEX
    entities: List[str]        # ["Apple", "Tim Cook", ...]
    claim_type: str           # factual, opinion, prediction
    input_type: InputType     # CLAIM, QUESTION, COMPARISON
```

#### FactChecker (LangGraph State Machine)

**File**: `agents/fact_checker.py`

**Purpose**: Search the web for evidence supporting/refuting the claim

**Internal Nodes**:
1. **Strategist**: Generates 3 targeted search queries
2. **Executor**: Runs parallel Tavily searches (async)
3. **Analyst**: Evaluates if evidence is sufficient

**State Machine**:
```
[START] → Strategist → Executor → Analyst → [Decision]
                                      │
                           ┌──────────┴──────────┐
                           │                     │
                      Sufficient            Insufficient
                           │                     │
                           ▼                     ▼
                        [END]              Strategist (retry)
                                           (max 2 iterations)
```

**Key Features**:
- **Caching**: MD5 hash of queries, stores results in memory
- **Parallel Execution**: Uses `asyncio.gather()` for concurrent searches
- **Adaptive Queries**: If first search is insufficient, generates new queries

#### ForensicExpert (Linguistic Analysis)

**File**: `agents/forensic_expert.py`

**Purpose**: Analyze claim for manipulation, bias, and source credibility

**Analysis Dimensions**:
1. **Emotional Language**: Detects sensational/manipulative phrasing
2. **Source Quality**: Evaluates cited sources (government, news, social media)
3. **Logical Fallacies**: Identifies strawman, ad hominem, false dichotomy
4. **Temporal Accuracy**: Checks if dates/timelines are plausible
5. **AI Detection**: Estimates if content is AI-generated

**Output**:
```python
{
    "manipulation_score": 0.3,  # 0-1
    "source_credibility": 0.8,
    "emotional_language_detected": ["shocking", "explosive"],
    "logical_fallacies": [],
    "verdict": "LIKELY_TRUE"
}
```

#### DevilsAdvocate (Adversarial Challenge)

**File**: `agents/devils_advocate.py`

**Purpose**: Actively try to DISPROVE the claim

**This is critical for reducing confirmation bias.** While the FactChecker looks for supporting evidence, the Devil's Advocate searches for contradictions.

**Process**:
1. **Identify Weak Points**: Find gaps in the supporting evidence
2. **Find Contradictions**: Search for sources that disagree
3. **Generate Counter-Arguments**: Create logical rebuttals
4. **Assess Attack Strength**: Rate how strong the case against is

**Output**:
```python
@dataclass
class DevilsAdvocateResult:
    counter_arguments: List[CounterArgument]
    weakest_points: List[str]
    contradicting_sources: List[Dict]
    overall_attack_strength: float  # 0.0-1.0
    recommendation: str  # "claim_likely_false", "claim_questionable", "claim_robust"
```

#### QuestionAnswerer (For Non-Claims)

**File**: `agents/question_answerer.py`

**Purpose**: Answer questions directly instead of TRUE/FALSE verification

**Triggered When**: Input is detected as `InputType.QUESTION` or `InputType.COMPARISON`

**Special Handling for Contentious Topics**:
```python
CONTENTIOUS_KEYWORDS = [
    'river dispute', 'kaveri', 'cauvery', 'kashmir',
    'palestine', 'israel', 'taiwan', 'ukraine', 'russia',
    'abortion', 'religion', 'caste', 'reservation',
]
```

For these topics, the agent:
- Acknowledges the dispute
- Presents ALL sides fairly
- Does NOT take sides
- Cites authoritative sources (courts, treaties, etc.)

**Output**:
```python
@dataclass
class AnswerResult:
    question: str
    answer: str
    summary: str
    nuance: Optional[str]  # For contentious topics
    sources: List[dict]
    confidence: float
    is_contentious: bool
```

---

## 6. Verification Pipeline

### 6.1 Complete Flow for a Claim

```
User Input: "Apple's market cap exceeded $3 trillion in 2024"
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: TRIAGE (0 LLM calls)                │
├─────────────────────────────────────────────────────────────────┤
│  Input Type: CLAIM                                              │
│  Domains: [TECH, FINANCE]                                       │
│  Complexity: MEDIUM                                             │
│  Entities: ["Apple", "$3 trillion", "2024"]                     │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 2: FACT CHECKING                       │
├─────────────────────────────────────────────────────────────────┤
│  Searches:                                                      │
│    • "Apple market cap 3 trillion 2024"                         │
│    • "Apple stock valuation history"                            │
│    • "largest company market cap 2024"                          │
│                                                                 │
│  Results: 12 sources found                                      │
│  Confidence: 0.85                                               │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: FORENSIC ANALYSIS                   │
├─────────────────────────────────────────────────────────────────┤
│  Manipulation Score: 0.1 (low)                                  │
│  Source Quality: 0.9 (Bloomberg, Reuters, CNBC)                 │
│  Logical Issues: None                                           │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 4: DEVIL'S ADVOCATE                    │
├─────────────────────────────────────────────────────────────────┤
│  Counter-Arguments:                                             │
│    • Market cap fluctuates, may have briefly touched but not    │
│      sustained $3T                                              │
│    • Different calculation methods yield different values       │
│                                                                 │
│  Attack Strength: 0.3 (weak)                                    │
│  Recommendation: "claim_robust"                                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 5: AI COUNCIL DEBATE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ROUND 1: Opening Statements                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PROSECUTOR: "While Apple is valuable, the $3T figure    │   │
│  │ was briefly touched in intraday trading, not a stable   │   │
│  │ market cap. This is misleading..."                      │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ DEFENDER: "Multiple authoritative sources confirm       │   │
│  │ Apple crossed $3T. Bloomberg, Reuters, and SEC filings  │   │
│  │ all corroborate this milestone..."                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ROUND 2: Rebuttals                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PROSECUTOR: [Attacks defender's evidence]               │   │
│  │ DEFENDER: [Counters prosecutor's arguments]             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  JURY VOTES:                                                    │
│  ┌─────────────┬────────┬────────────────────────────────┐     │
│  │ The Skeptic │  TRUE  │ "Evidence is overwhelming"     │     │
│  │ The Pragmatist│ TRUE │ "Real-world impact confirms"  │     │
│  │ The Scientist│  TRUE │ "Data from multiple sources"  │     │
│  └─────────────┴────────┴────────────────────────────────┘     │
│                                                                 │
│  VERDICT: TRUE (3-0 unanimous)                                  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 6: FINAL JUDGMENT                      │
├─────────────────────────────────────────────────────────────────┤
│  The Judge synthesizes all evidence:                            │
│                                                                 │
│  VERDICT: TRUE                                                  │
│  CONFIDENCE: 92%                                                │
│  SUMMARY: "Apple's market capitalization did exceed $3          │
│           trillion in 2024, confirmed by multiple financial     │
│           news sources and SEC filings."                        │
│                                                                 │
│  KEY EVIDENCE:                                                  │
│    • Bloomberg: "Apple hits $3T milestone" (Jan 2024)           │
│    • Reuters: "Tech giant valuation record"                     │
│    • SEC 10-K Filing                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Complexity-Based Routing

Not all claims need the full pipeline:

| Complexity | Agents Used | LLM Calls | Latency |
|------------|-------------|-----------|---------|
| **SIMPLE** | FactChecker → Judge | 4-6 | 10-15s |
| **MEDIUM** | FactChecker → ForensicExpert → Council → Judge | 8-12 | 20-30s |
| **COMPLEX** | DomainAgents → FactChecker → ForensicExpert → Devil's Advocate → Council → Judge | 15-20 | 30-45s |

---

## 7. Question vs Claim Detection

### 7.1 Detection Logic

The system distinguishes between three input types:

```python
class InputType(Enum):
    CLAIM = "claim"        # "Apple is worth $3T" → Verify
    QUESTION = "question"  # "Who owns Apple?" → Answer
    COMPARISON = "comparison"  # "Apple vs Microsoft?" → Analyze
```

### 7.2 Detection Patterns

```python
# Questions (regex patterns)
QUESTION_PATTERNS = [
    r'^(who|what|where|when|why|how|which|whose|whom)\s',
    r'^(is|are|was|were|do|does|did|can|could|will|would|should)\s.*\?',
    r'\?$',  # Ends with question mark
]

# Comparisons
COMPARISON_PATTERNS = [
    r'\b(or)\b.*\?',           # "X or Y?"
    r'\b(vs|versus)\b',        # "X vs Y"
    r'\b(compared to|better than|worse than)\b',
]
```

### 7.3 Response Difference

| Input Type | Response Format |
|------------|-----------------|
| **CLAIM** | `{ verdict: "TRUE/FALSE/UNCERTAIN", confidence: 0.92, sources: [...] }` |
| **QUESTION** | `{ answer: "Tim Cook is...", summary: "...", sources: [...] }` |
| **COMPARISON** | `{ answer: "Both have merits...", nuance: "...", is_contentious: true }` |

---

## 8. AI Council Debate System

### 8.1 Philosophy

The AI Council is inspired by the **adversarial legal system**:

- **Prosecutor**: Argues the claim is FALSE
- **Defender**: Argues the claim is TRUE
- **Jury**: Neutral observers who vote after hearing both sides

This adversarial approach helps:
1. Expose weaknesses in evidence
2. Surface counter-arguments
3. Reduce single-agent bias
4. Increase verdict reliability

### 8.2 Debate Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                       AI COUNCIL SESSION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ROUND 1: OPENING STATEMENTS                                     │
│  ├── Prosecutor presents case for FALSE                          │
│  └── Defender presents case for TRUE                             │
│                                                                  │
│  ROUND 2: EVIDENCE CHALLENGE (optional for complex)              │
│  ├── Prosecutor attacks weakest supporting evidence              │
│  └── Defender defends evidence, attacks counter-evidence         │
│                                                                  │
│  ROUND 3: REBUTTALS                                              │
│  ├── Prosecutor responds to Defender's arguments                 │
│  └── Defender responds to Prosecutor's arguments                 │
│                                                                  │
│  ROUND 4: CLOSING STATEMENTS (optional for complex)              │
│  ├── Prosecutor summarizes case for FALSE                        │
│  └── Defender summarizes case for TRUE                           │
│                                                                  │
│  JURY DELIBERATION                                               │
│  ├── Each juror independently evaluates arguments                │
│  ├── Each juror casts vote: TRUE / FALSE / UNCERTAIN             │
│  └── Majority determines council verdict                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Juror Personas

Each juror has a unique perspective:

```python
JUROR_PERSONAS = [
    {
        "id": "skeptic",
        "name": "The Skeptic",
        "description": "Requires strong evidence. High bar for proof.",
        "temperature": 0.1  # Very deterministic
    },
    {
        "id": "pragmatist",
        "name": "The Pragmatist", 
        "description": "Common sense approach. Weighs practical implications.",
        "temperature": 0.4
    },
    {
        "id": "scientist",
        "name": "The Scientist",
        "description": "Data-driven analysis. Statistical evidence.",
        "temperature": 0.1
    }
]
```

### 8.4 Vote Aggregation

```python
def determine_verdict(votes: List[JurorVote]) -> Vote:
    vote_counts = {"TRUE": 0, "FALSE": 0, "UNCERTAIN": 0}
    for vote in votes:
        vote_counts[vote.vote.value] += 1
    
    # Majority wins
    max_vote = max(vote_counts, key=vote_counts.get)
    
    # If tie or majority UNCERTAIN, verdict is UNCERTAIN
    if vote_counts["UNCERTAIN"] >= len(votes) / 2:
        return Vote.UNCERTAIN
    
    return Vote[max_vote]
```

---

## 9. Truth Market (Prediction Market)

### 9.1 Concept

The Truth Market is a **Polymarket-style prediction market** where users bet on whether Aletheia's verdicts are correct.

```
┌─────────────────────────────────────────────────────────────────┐
│                       TRUTH MARKET                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CLAIM: "Apple's market cap exceeded $3 trillion"                │
│  ALETHEIA VERDICT: TRUE (92% confidence)                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  BET: Is Aletheia correct?                                  ││
│  │                                                             ││
│  │  ┌───────────────┐         ┌───────────────┐                ││
│  │  │   CORRECT     │         │    WRONG      │                ││
│  │  │   75% odds    │         │   25% odds    │                ││
│  │  │   Pool: 7500  │         │   Pool: 2500  │                ││
│  │  └───────────────┘         └───────────────┘                ││
│  │                                                             ││
│  │  [Place Bet: 100 ALETH] [Position: CORRECT]                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  MARKET STATUS: OPEN                                             │
│  CLOSES: 7 days from creation                                    │
│  RESOLUTION: Community verification or admin                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Market Lifecycle

```
PENDING → OPEN → CLOSED → RESOLVED
            │                  │
            │                  ├── ALETHEIA_CORRECT (bettors on CORRECT win)
            │                  ├── ALETHEIA_WRONG (bettors on WRONG win)
            │                  └── VOIDED (all bets refunded)
            │
            └── DISPUTED (under review)
```

### 9.3 Odds Calculation

Odds are calculated using the **pool ratio**:

```python
@property
def correct_odds(self) -> float:
    """Probability implied by betting for 'correct'."""
    if self.total_pool == 0:
        return 0.5
    return self.wrong_pool / self.total_pool

@property
def wrong_odds(self) -> float:
    """Probability implied by betting for 'wrong'."""
    if self.total_pool == 0:
        return 0.5
    return self.correct_pool / self.total_pool
```

### 9.4 Payout Calculation

```python
def calculate_payout(bet: Bet, outcome: ResolutionOutcome) -> float:
    market = markets[bet.market_id]
    
    if outcome == ResolutionOutcome.VOIDED:
        return bet.amount  # Full refund
    
    if bet.position == BetPosition.CORRECT and outcome == ResolutionOutcome.ALETHEIA_CORRECT:
        # Winner: gets share of losing pool
        share = bet.amount / market.correct_pool
        winnings = share * market.wrong_pool
        return bet.amount + winnings
    
    if bet.position == BetPosition.WRONG and outcome == ResolutionOutcome.ALETHEIA_WRONG:
        share = bet.amount / market.wrong_pool
        winnings = share * market.correct_pool
        return bet.amount + winnings
    
    return 0  # Lost bet
```

### 9.5 Data Models

```python
@dataclass
class Market:
    market_id: str
    claim: str
    claim_hash: str
    
    # Aletheia's verdict
    aletheia_verdict: str  # "TRUE", "FALSE", "UNCERTAIN"
    aletheia_confidence: float
    verdict_summary: str
    
    # Pools
    correct_pool: float = 0.0
    wrong_pool: float = 0.0
    
    # Status
    status: MarketStatus = MarketStatus.OPEN
    resolution: Optional[ResolutionOutcome] = None

@dataclass
class Bet:
    bet_id: str
    user_id: str
    market_id: str
    position: BetPosition
    amount: float
    odds_at_bet: float
    potential_payout: float
    status: str  # active, won, lost, refunded

@dataclass
class User:
    user_id: str
    username: str
    balance: float  # ALETH tokens
    total_bets: int
    wins: int
    losses: int
    total_profit: float
```

---

## 10. Frontend Architecture

### 10.1 Component Hierarchy

```
App (layout.tsx)
├── ThemeProvider (dark/light mode)
│   └── Page (page.tsx)
│       ├── Navbar
│       │   ├── Logo
│       │   └── ModeToggle
│       │
│       ├── SearchHero
│       │   └── Input + Submit Button
│       │
│       ├── VerificationProgress (during loading)
│       │   └── Log entries (real-time)
│       │
│       └── VerificationResult (after completion)
│           ├── VerdictBadge (TRUE/FALSE/UNCERTAIN)
│           ├── ConfidenceBar
│           ├── SummaryCard
│           ├── SourcesList
│           └── DebateTranscript (collapsible)
```

### 10.2 State Management

```tsx
// Main page state (page.tsx)
const [isLoading, setIsLoading] = useState(false);
const [result, setResult] = useState<VerificationResult | null>(null);
const [error, setError] = useState<string | null>(null);
const [logs, setLogs] = useState<Log[]>([]);
const [sources, setSources] = useState<Source[]>([]);
```

### 10.3 Streaming Response Handler

The frontend handles Server-Sent Events (SSE) from the backend:

```tsx
const reader = res.body?.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");

    for (const line of lines) {
        if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));

            switch (data.type) {
                case "log":
                    setLogs(prev => [...prev, data]);
                    break;
                case "sources":
                    setSources(prev => [...prev, ...data.data]);
                    break;
                case "result":
                    setResult(data.data);
                    break;
                case "answer":
                    setResult({ ...data, is_answer: true });
                    break;
            }
        }
    }
}
```

### 10.4 Real-Time Event Types

| Event Type | Description | UI Update |
|------------|-------------|-----------|
| `status` | Phase change | Update progress indicator |
| `triage` | Input classified | Show domains, complexity |
| `log` | Agent message | Append to log list |
| `sources` | Found sources | Add to sources panel |
| `agent` | Agent complete | Show agent verdict |
| `debate_round` | Council debate | Add debate transcript |
| `jury_vote` | Juror voted | Show individual vote |
| `result` | Final verdict | Display result card |
| `answer` | Question answered | Display answer card |
| `error` | Error occurred | Show error message |

---

## 11. API Reference

### 11.1 Endpoints Overview

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Health check | None |
| `GET` | `/health` | Detailed health | None |
| `POST` | `/verify_stream` | Stream verification | Rate limited |
| `POST` | `/verify` | Non-streaming verify | Rate limited |
| `POST` | `/market/create` | Create market | None |
| `GET` | `/market/{id}` | Get market | None |
| `POST` | `/market/bet` | Place bet | None |
| `POST` | `/market/resolve` | Resolve market | **Admin only** |
| `GET` | `/markets` | List all markets | None |
| `POST` | `/user/create` | Create user | None |
| `GET` | `/user/{id}` | Get user | None |

### 11.2 Request/Response Examples

#### Verify Claim (Streaming)

```http
POST /verify_stream
Content-Type: application/json

{
    "claim": "Apple's market cap exceeded $3 trillion in 2024"
}
```

**Response (SSE Stream)**:
```
data: {"type": "status", "phase": "triage", "message": "Analyzing input..."}

data: {"type": "triage", "data": {"domains": ["tech", "finance"], "complexity": "medium", "input_type": "claim"}}

data: {"type": "status", "phase": "fact_check", "message": "Searching for evidence..."}

data: {"type": "sources", "data": [{"url": "https://...", "title": "...", "content": "..."}]}

data: {"type": "agent", "agent": "FactChecker", "verdict": "LIKELY_TRUE"}

data: {"type": "debate_round", "round": 1, "type": "opening"}

data: {"type": "jury_vote", "juror": "The Skeptic", "vote": "TRUE"}

data: {"type": "result", "data": {"verdict": "TRUE", "confidence": 0.92, "summary": "..."}}

data: [DONE]
```

#### Place Bet

```http
POST /market/bet
Content-Type: application/json

{
    "user_id": "user_abc123",
    "market_id": "mkt_xyz789",
    "position": "correct",
    "amount": 100.0
}
```

**Response**:
```json
{
    "success": true,
    "bet": {
        "bet_id": "bet_def456",
        "user_id": "user_abc123",
        "market_id": "mkt_xyz789",
        "position": "correct",
        "amount": 100.0,
        "odds_at_bet": 1.5,
        "potential_payout": 150.0,
        "status": "active"
    },
    "new_balance": 900.0
}
```

### 11.3 Input Validation

```python
class ClaimRequest(BaseModel):
    claim: str = Field(
        ..., 
        min_length=3,      # MIN_CLAIM_LENGTH
        max_length=2000    # MAX_CLAIM_LENGTH
    )

class BetRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    market_id: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., pattern="^(correct|wrong)$")
    amount: float = Field(..., gt=0, le=10000)
```

---

## 12. Security Implementation

### 12.1 Security Measures

| Category | Implementation | Status |
|----------|----------------|--------|
| **CORS** | Restricted to `localhost:3000` + env var | ✅ |
| **Rate Limiting** | 30 requests/minute per IP | ✅ |
| **Input Sanitization** | Prompt injection patterns removed | ✅ |
| **Input Length** | Max 2000 characters | ✅ |
| **Admin Auth** | `X-Admin-Key` header required | ✅ |
| **Bet Validation** | Positive amount, max 10000 | ✅ |
| **Command Injection** | `os.system` → `subprocess.run` | ✅ |

### 12.2 Rate Limiting Implementation

```python
RATE_LIMIT_REQUESTS = 30  # requests per minute
rate_limit_store: dict = {}

def check_rate_limit(client_ip: str) -> bool:
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
    
    rate_limit_store[client_ip].append(now)
    return True
```

### 12.3 Input Sanitization

```python
def sanitize_input(text: str) -> str:
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # Remove prompt injection patterns
    dangerous_patterns = [
        r'ignore\s+(previous|above|all)\s+instructions?',
        r'you\s+are\s+now\s+',
        r'system\s*:',
        r'<\|.*?\|>',
        r'\[INST\]',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()
```

### 12.4 Admin Authentication

```python
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-in-production")

def verify_admin_key(x_admin_key: str = Header(None)) -> bool:
    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True

@app.post("/market/resolve")
def resolve_market(
    request: ResolveRequest,
    admin_verified: bool = Depends(verify_admin_key)  # Protected
):
    ...
```

---

## 13. Data Flow Diagrams

### 13.1 Claim Verification Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────▶│ Frontend │────▶│ Backend  │────▶│  Groq    │
│ Browser  │     │ Next.js  │     │ FastAPI  │     │  LLM     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │
     │   1. Submit    │                │                │
     │   claim        │                │                │
     │ ───────────────▶                │                │
     │                │  2. POST       │                │
     │                │  /verify_stream│                │
     │                │ ───────────────▶                │
     │                │                │  3. Generate   │
     │                │                │  queries       │
     │                │                │ ───────────────▶
     │                │                │                │
     │                │                │◀─ 4. Queries ──│
     │                │                │                │
     │                │                │  5. Search     │
     │                │                │ ────────────┐  │
     │                │                │             │  │
     │                │                │             ▼  │
     │                │                │      ┌──────────┐
     │                │                │      │  Tavily  │
     │                │                │      │  Search  │
     │                │                │      └──────────┘
     │                │                │             │
     │                │                │◀────────────┘
     │                │                │                │
     │                │                │  6. Analyze    │
     │                │                │ ───────────────▶
     │                │                │                │
     │                │◀── 7. Stream ──│                │
     │                │    events      │                │
     │◀── 8. Update ──│                │                │
     │    UI          │                │                │
     │                │                │                │
```

### 13.2 Market Betting Flow

```
┌──────────┐     ┌──────────┐     ┌──────────────────────────────┐
│  User    │────▶│ Backend  │────▶│      Market Manager          │
└──────────┘     └──────────┘     │  ┌─────────┐ ┌─────────┐    │
                                  │  │  Users  │ │ Markets │    │
                                  │  └─────────┘ └─────────┘    │
                                  │  ┌─────────┐                │
                                  │  │  Bets   │                │
                                  │  └─────────┘                │
                                  └──────────────────────────────┘

1. User places bet
   POST /market/bet {user_id, market_id, position: "correct", amount: 100}

2. Manager validates:
   - User has sufficient balance
   - Market is open
   - Bet amount > 0 and <= 10000

3. Manager updates:
   - User.balance -= 100
   - Market.correct_pool += 100
   - New Bet created

4. When market resolves:
   - Winners get proportional share of loser pool
   - User.balance += payout
   - Bet.status = "won" or "lost"
```

---

## 14. Deployment Architecture

### 14.1 Docker Compose Setup

```yaml
services:
  backend:
    build: ./backend
    container_name: aletheia-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend/storage:/app/storage
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: aletheia-frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

networks:
  default:
    name: aletheia-network
```

### 14.2 Environment Variables

```bash
# .env file
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
ADMIN_API_KEY=your-secure-admin-key
FRONTEND_URL=http://localhost:3000
```

### 14.3 Production Recommendations

| Component | Development | Production |
|-----------|-------------|------------|
| **CORS** | `localhost:3000` | Your domain |
| **Database** | In-memory | PostgreSQL |
| **Rate Limit Store** | In-memory dict | Redis |
| **Admin Key** | Default value | Strong secret |
| **Logging** | Console | Structured (JSON) |
| **SSL** | None | Required |

---

## 15. Future Roadmap

### Phase 1: Core Improvements (Current)
- [x] Multi-agent verification
- [x] AI Council debate
- [x] Question answering
- [x] Security hardening
- [ ] Persistent storage (PostgreSQL)
- [ ] Redis for rate limiting

### Phase 2: Truth Market UI
- [ ] Market listing page
- [ ] User dashboard
- [ ] Betting interface
- [ ] Leaderboard
- [ ] Market resolution workflow

### Phase 3: SingularityNET Integration
- [ ] Agent registration on SingularityNET
- [ ] AGIX token integration
- [ ] Decentralized agent marketplace
- [ ] Agent reputation system

### Phase 4: Advanced Features
- [ ] Multi-language support
- [ ] Image/video fact-checking
- [ ] Browser extension
- [ ] Mobile app
- [ ] Real-time news monitoring

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Claim** | A statement that can be verified as TRUE or FALSE |
| **Triage** | Initial classification of input (domains, complexity, type) |
| **Domain Agent** | Specialized agent for specific topics (Tech, Finance, etc.) |
| **Devil's Advocate** | Agent that tries to DISPROVE claims |
| **AI Council** | Adversarial debate with Prosecutor, Defender, Jury |
| **Juror Persona** | Unique perspective (Skeptic, Pragmatist, Scientist) |
| **Truth Market** | Prediction market for betting on verdict correctness |
| **ALETH** | Virtual token used in Truth Market |
| **Pool** | Total amount bet on one position (correct/wrong) |
| **Resolution** | Final determination of whether Aletheia was correct |

---

## Appendix B: FAQ

**Q: How accurate is Aletheia?**
A: Accuracy depends on claim complexity and available sources. Simple factual claims have ~90% accuracy. Complex, recent, or obscure claims may be lower.

**Q: Why use multiple agents instead of one?**
A: Multiple agents with different roles (fact-checker, devil's advocate, jury) reduce bias and provide more balanced analysis.

**Q: Can users dispute verdicts?**
A: Yes, through the Truth Market. If many users bet "wrong," it signals potential inaccuracy.

**Q: What LLM does Aletheia use?**
A: Groq with Llama 3.1 8B Instant for fast inference (~200ms per call).

**Q: Is the Truth Market using real money?**
A: No, it uses virtual ALETH tokens. Real money integration would require regulatory compliance.

---

*Last Updated: December 2024*
*Version: 2.0.0*
*Team: Team Without You*
