# MoveH Edge Cases and Solutions

This document outlines the known edge cases, limitations, and proposed solutions for the MoveH fact-checking system.

---

## Table of Contents

1. [Search and Evidence Collection](#1-search-and-evidence-collection)
2. [Claim Classification](#2-claim-classification)
3. [Forensic Analysis Limitations](#3-forensic-analysis-limitations)
4. [Verdict Synthesis Logic](#4-verdict-synthesis-logic)
5. [Blockchain and Storage](#5-blockchain-and-storage)
6. [Security Vulnerabilities](#6-security-vulnerabilities)
7. [Feature Gaps](#7-feature-gaps)
8. [Implementation Priority](#8-implementation-priority)

---

## 1. Search and Evidence Collection

### 1.1 No Internet Results

**Problem**: The Tavily API returns no results for a given claim, leaving the Fact Checker agent without evidence.

**Current Behavior**: Falls back to simulated or empty results, leading to an "UNVERIFIED" verdict.

**Solution**:
- Implement multiple search provider fallbacks (Google Custom Search, Bing API, DuckDuckGo API)
- If all providers return no results, flag the claim as `NEEDS_HUMAN_REVIEW` rather than issuing an uncertain verdict
- Log the failure for monitoring and pattern analysis

### 1.2 Breaking News (Temporal Gap)

**Problem**: Claims about very recent events may not yet be indexed by search engines.

**Current Behavior**: Returns "UNVERIFIABLE" which may be cached, preventing future verification.

**Solution**:
- Implement temporal context extraction from the claim text
- Detect phrases indicating recency ("today", "just now", "breaking", "moments ago")
- Return `TOO_EARLY_TO_VERIFY` status with a short cache TTL (1-2 hours)
- Include a `retry_after` timestamp in the response

### 1.3 Paywalled Sources

**Problem**: High-quality sources (Bloomberg, WSJ, FT) are often behind paywalls, limiting access to full article content.

**Current Behavior**: Only retrieves snippets, potentially missing critical context.

**Solution**:
- Integrate premium news APIs with subscription access (Factiva, LexisNexis, NewsAPI Premium)
- Query Internet Archive (Wayback Machine) for cached versions
- Implement content extraction from available metadata and snippets
- Weight paywall-accessible snippets lower than full-text sources

### 1.4 Non-English Claims

**Problem**: Search and analysis are primarily optimized for English-language content.

**Current Behavior**: Poor or no results for claims in other languages.

**Solution**:
- Implement language detection as the first pipeline step
- Use translation APIs (Google Translate, DeepL) to normalize claims to English
- Execute parallel searches in both the original language and English
- Translate results back for consistency
- Store the original language in claim metadata

### 1.5 Obscure or Niche Topics

**Problem**: Claims about specialized topics may not appear in mainstream news sources.

**Current Behavior**: Insufficient evidence leads to uncertain verdicts.

**Solution**:
- Add domain-specific search integrations:
  - Academic: Semantic Scholar, PubMed, arXiv
  - Government: Data.gov, official government portals
  - Financial: SEC EDGAR, company filings
  - Scientific: CrossRef, Google Scholar
- Implement topic classification to route claims to appropriate specialized sources

---

## 2. Claim Classification

### 2.1 Time-Sensitive Claims

**Problem**: Claims about current state ("Bitcoin is at $50,000") become outdated quickly.

**Current Behavior**: Verdict may be cached with no expiration awareness.

**Solution**:
- Extract temporal markers and classify claim temporality
- Implement claim types with appropriate TTL values:
  - `REAL_TIME_STATE`: 1 hour expiry
  - `DAILY_STATE`: 24 hour expiry
  - `HISTORICAL_FACT`: No expiry
- Store verification timestamp prominently
- Re-verify on access if expiry has passed

### 2.2 Predictions and Future Claims

**Problem**: Claims about future events cannot be fact-checked.

**Current Behavior**: Treated as regular claims, resulting in misleading verdicts.

**Solution**:
- Implement future tense detection ("will", "going to", "expected to", "predicted")
- Return `PREDICTION_NOT_VERIFIABLE` classification
- Provide context on what would be needed to verify once the event occurs
- Optionally store for future verification when the predicted date passes

### 2.3 Satire and Parody

**Problem**: Satirical content may be incorrectly marked as FALSE.

**Current Behavior**: No distinction between intentional satire and misinformation.

**Solution**:
- Maintain a database of known satire sources (The Onion, Babylon Bee, The Daily Mash)
- Check source attribution against the satire database
- Return `SATIRE` classification with explanation
- Detect common satire markers in content structure

### 2.4 Opinion Statements

**Problem**: Subjective opinions cannot be fact-checked as true or false.

**Current Behavior**: Opinions are processed as factual claims.

**Solution**:
- Implement opinion detection using linguistic markers:
  - Subjective phrases: "I think", "I believe", "in my opinion"
  - Comparative judgments: "best", "worst", "better than"
  - Normative statements: "should", "ought to", "must"
- Return `OPINION_NOT_FACT` classification
- Distinguish between opinions and factual claims embedded within opinions

### 2.5 Evolving Stories

**Problem**: Ongoing news stories may have verdicts that become outdated as new information emerges.

**Current Behavior**: Initial verdict is cached without update mechanism.

**Solution**:
- Implement verdict versioning with `supersedes` field
- Track claim evolution through related verdict chains
- Set shorter expiry for claims classified as `ONGOING_STORY`
- Provide verdict history in responses

---

## 3. Forensic Analysis Limitations

### 3.1 Professionally Written Misinformation

**Problem**: High-quality writing may produce high integrity scores despite containing false information.

**Current Behavior**: Writing quality positively influences integrity score regardless of factual accuracy.

**Solution**:
- Decouple writing quality assessment from credibility assessment
- Implement source reputation scoring as an independent factor
- Cross-reference claims against known misinformation databases
- Weight factual verification higher than stylistic analysis when evidence is available

### 3.2 Sophisticated AI-Generated Content

**Problem**: Advanced language models produce text that evades current AI detection methods.

**Current Behavior**: AI detection may fail for sophisticated generated content.

**Solution**:
- Integrate multiple AI detection services (GPTZero, Originality.ai, Copyleaks)
- Use ensemble voting across detectors
- Track detection confidence and flag low-confidence results
- Continuously update detection methods as models evolve

### 3.3 Legitimate Urgent Communication

**Problem**: Real emergencies use the same urgency markers as scam content.

**Current Behavior**: Urgency words trigger penalties regardless of context.

**Solution**:
- Implement context-aware urgency analysis
- Consider source credibility when evaluating urgency
- Differentiate categories:
  - Emergency services context: Lower penalty
  - Financial/personal action requests: Higher penalty
- Analyze the requested action, not just the language

### 3.4 Context-Dependent Terminology

**Problem**: Words like "crash", "surge", "break" have different implications across domains.

**Current Behavior**: Terms are evaluated without domain context.

**Solution**:
- Implement domain classification as a preprocessing step
- Maintain domain-specific lexicons with contextual weights
- Adjust penalty calculations based on detected domain
- Consider industry-standard terminology in professional contexts

---

## 4. Verdict Synthesis Logic

### 4.1 Agent Disagreement

**Problem**: When the Fact Checker and Forensic Expert produce conflicting signals, the final verdict may be unreliable.

**Current Behavior**: Weighted average is computed, potentially masking significant disagreement.

**Solution**:
- Implement disagreement detection threshold
- When agents diverge significantly (>40% difference), trigger additional analysis:
  - Deploy a specialized "Tiebreaker" agent with focused investigation
  - Queue for human review
- Include disagreement flag in verdict metadata
- Provide separate agent conclusions in the response

### 4.2 Mutual Uncertainty

**Problem**: When both agents return uncertain results, the combined verdict lacks reliability.

**Current Behavior**: Returns "UNCERTAIN" verdict with low confidence.

**Solution**:
- Implement automatic escalation to human review queue
- Set reduced cache TTL for uncertain verdicts (1 hour)
- Trigger expanded search with alternative queries
- Clearly communicate the limitations in the response

### 4.3 Threshold Sensitivity

**Problem**: Small score differences near decision boundaries produce categorically different verdicts.

**Current Behavior**: Hard cutoffs (e.g., 0.50 vs 0.51) produce different verdict categories.

**Solution**:
- Implement probability ranges with explicit uncertainty bands:
  - 0.00-0.20: FALSE
  - 0.20-0.35: PROBABLY_FALSE
  - 0.35-0.65: UNCERTAIN
  - 0.65-0.80: PROBABLY_TRUE
  - 0.80-1.00: TRUE
- Report raw probability alongside categorical verdict
- Widen the uncertain band to acknowledge genuine ambiguity

---

## 5. Blockchain and Storage

### 5.1 Semantic Duplicates

**Problem**: Rephrased claims ("Elon Musk bought Twitter" vs "Twitter was acquired by Musk") generate different hashes and bypass deduplication.

**Current Behavior**: Only exact hash matches are deduplicated.

**Solution**:
- Generate semantic embeddings for each claim using a sentence transformer model
- Store embeddings alongside claim hashes
- Implement vector similarity search with configurable threshold (recommended: 0.92)
- Return existing verdict when semantic similarity exceeds threshold
- Maintain mapping between similar claims for audit purposes

### 5.2 Expired Verdicts

**Problem**: Time-sensitive verdicts may be returned after they are no longer valid.

**Current Behavior**: Expiry field exists but may not be consistently enforced.

**Solution**:
- Implement expiry checking on all verdict retrievals
- Trigger automatic re-verification for expired verdicts on access
- Display verification timestamp and expiry status to users
- Implement background re-verification for frequently accessed expired verdicts

### 5.3 Transaction Failures

**Problem**: Insufficient gas or network issues may prevent blockchain submission.

**Current Behavior**: Transaction failure may result in lost verdict.

**Solution**:
- Implement transaction queue with retry logic
- Maintain minimum wallet balance with automated top-up alerts
- Store verdicts in local database before blockchain submission
- Implement batch submission for cost efficiency during high volume
- Consider gasless transactions (meta-transactions) for improved reliability

### 5.4 Storage Provider Unavailability

**Problem**: Shelby Protocol downtime prevents PDF report storage.

**Current Behavior**: Single point of failure for evidence storage.

**Solution**:
- Implement multi-provider storage strategy:
  - Primary: Shelby Protocol
  - Secondary: IPFS
  - Tertiary: Arweave
- Store CIDs from all successful uploads
- Implement health checking and automatic failover
- Verify content availability periodically

---

## 6. Security Vulnerabilities

### 6.1 Prompt Injection

**Problem**: Malicious claims may contain instructions intended to manipulate LLM behavior.

**Risk Level**: High

**Solution**:
- Implement input sanitization layer before processing:
  ```
  Patterns to filter:
  - "ignore.*instructions"
  - "you are now"
  - "system:.*"
  - "assistant:.*"
  - Role-switching attempts
  ```
- Use separate system prompts that cannot be overridden
- Implement output validation to detect anomalous responses
- Log and alert on detected injection attempts

### 6.2 Source Flooding

**Problem**: Attackers may create multiple fake sources to establish false consensus.

**Risk Level**: Medium

**Solution**:
- Implement source reputation scoring:
  - Domain age (penalize domains < 30 days)
  - Historical accuracy tracking
  - Cross-reference with known reliable source databases
- Detect source clustering (multiple domains, same registrant)
- Weight established sources higher than new or unknown sources
- Implement source diversity requirements (minimum N distinct publishers)

### 6.3 Timing Attacks

**Problem**: Submitting claims before news is indexed may result in cached "UNVERIFIABLE" verdicts.

**Risk Level**: Medium

**Solution**:
- Implement variable TTL based on verdict confidence:
  - HIGH confidence: Long TTL (30 days)
  - MEDIUM confidence: Medium TTL (7 days)
  - LOW confidence: Short TTL (1 hour)
  - UNVERIFIABLE: Very short TTL (1 hour)
- Never permanently cache uncertain verdicts
- Implement re-verification triggers based on evidence availability changes

### 6.4 Semantic Manipulation

**Problem**: Claims may be technically true but contextually misleading.

**Risk Level**: Medium

**Solution**:
- Implement "MISLEADING" verdict category
- Detect common manipulation patterns:
  - Cherry-picked statistics
  - Out-of-context quotes
  - Technically true but deceptive framing
- Provide full context in verdict reasoning
- Flag claims that require nuanced interpretation

---

## 7. Feature Gaps

### 7.1 Visual Content Verification

**Current State**: No capability to verify images or videos.

**Impact**: Cannot detect deepfakes, manipulated images, or false image attributions.

**Proposed Solution**:
- Integrate reverse image search APIs (Google Vision, TinEye)
- Implement deepfake detection API integration
- Extract and verify image metadata (EXIF data)
- Check image provenance against source claims

### 7.2 Multi-Language Support

**Current State**: English-only processing.

**Impact**: Unable to serve non-English speaking users or verify claims from non-English sources.

**Proposed Solution**:
- Implement language detection at input
- Integrate translation APIs for claim normalization
- Deploy language-specific search configurations
- Store original language and provide translated verdicts

### 7.3 Source Credibility Database

**Current State**: No systematic source reputation tracking.

**Impact**: All sources treated equally regardless of historical reliability.

**Proposed Solution**:
- Integrate external credibility databases:
  - Media Bias/Fact Check
  - NewsGuard
  - Wikipedia reliable sources list
- Implement internal reputation tracking based on historical accuracy
- Weight source credibility in verdict calculation

### 7.4 Human Review Integration

**Current State**: Fully automated with no escalation path.

**Impact**: No recourse for edge cases requiring human judgment.

**Proposed Solution**:
- Implement review queue for low-confidence verdicts
- Build administrative dashboard for human reviewers
- Define escalation criteria (confidence < 0.6, agent disagreement, etc.)
- Track human review decisions to improve automated models

### 7.5 Claim Similarity Matching

**Current State**: Only exact hash matching for deduplication.

**Impact**: Semantically identical claims processed redundantly.

**Proposed Solution**:
- Store semantic embeddings for all processed claims
- Implement approximate nearest neighbor search
- Return existing verdicts for semantically similar claims
- Track claim clusters for trend analysis

---

## 8. Implementation Priority

### High Priority

These items address critical functionality gaps or security concerns:

| Item | Rationale | Estimated Effort |
|------|-----------|------------------|
| Semantic similarity deduplication | Significant cost and efficiency impact | Medium |
| Source reputation database | Core accuracy improvement | Medium |
| Human review queue | Essential for edge case handling | Medium |
| Input sanitization | Security requirement | Low |
| Variable TTL for uncertain verdicts | Prevents stale misinformation | Low |

### Medium Priority

These items improve system robustness and coverage:

| Item | Rationale | Estimated Effort |
|------|-----------|------------------|
| Multi-language support | Expands addressable market | High |
| Claim type detection | Prevents inappropriate verdicts | Medium |
| Multiple search providers | Improves evidence collection | Medium |
| External AI detection integration | Improves forensic accuracy | Low |
| Multi-provider storage | Improves reliability | Low |

### Lower Priority

These items provide additional value but are not critical:

| Item | Rationale | Estimated Effort |
|------|-----------|------------------|
| Image and video verification | New capability, significant scope | High |
| Tiebreaker agent | Marginal accuracy improvement | Medium |
| Real-time re-verification | Improved freshness | Medium |
| Domain-specific search routing | Niche improvement | Medium |

---

## Appendix: Quick Implementation Reference

### Satire Source Detection

```python
SATIRE_SOURCES = [
    "theonion.com",
    "babylonbee.com",
    "thedailymash.co.uk",
    "clickhole.com",
    "thebeaverton.com",
    "waterfordwhispersnews.com",
    "newsthump.com"
]

def is_satire_source(url: str) -> bool:
    domain = extract_domain(url)
    return domain in SATIRE_SOURCES
```

### Opinion Detection

```python
OPINION_MARKERS = [
    r"\bi think\b",
    r"\bi believe\b",
    r"\bin my opinion\b",
    r"\bshould\b",
    r"\bthe best\b",
    r"\bthe worst\b",
    r"\bbetter than\b",
    r"\bworse than\b"
]

def is_opinion(claim: str) -> bool:
    claim_lower = claim.lower()
    return any(re.search(pattern, claim_lower) for pattern in OPINION_MARKERS)
```

### Input Sanitization

```python
DANGEROUS_PATTERNS = [
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"you\s+are\s+now",
    r"^system\s*:",
    r"^assistant\s*:",
    r"pretend\s+to\s+be",
    r"act\s+as\s+if"
]

def sanitize_input(claim: str) -> str:
    sanitized = claim
    for pattern in DANGEROUS_PATTERNS:
        sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
    return sanitized
```

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Maintainers: MoveH Development Team*
