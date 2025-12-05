"""
Claim Processor - MoveH

Processes claims for on-chain storage preparation:
- Generates claim hash (for exact matching)
- Extracts keywords (for semantic search)
- Detects claim type (for freshness rules)
- Calculates expiry time (based on claim type)
"""

import os
import re
import hashlib
import time
from datetime import datetime, timedelta
from typing import TypedDict, Literal
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)


# ============ Claim Type Definitions ============

class ClaimType:
    """Claim type constants with freshness rules."""
    TIMELESS = 0        # Scientific facts, math - never expires
    HISTORICAL = 1      # Past events with fixed dates - never expires
    BREAKING_NEWS = 2   # Recent events, announcements - 7 days
    ONGOING = 3         # Current prices, live situations - 24 hours
    PREDICTION = 4      # Future events, forecasts - until target date
    STATUS = 5          # Current state of person/company - 30 days
    
    NAMES = {
        0: "TIMELESS",
        1: "HISTORICAL",
        2: "BREAKING_NEWS",
        3: "ONGOING",
        4: "PREDICTION",
        5: "STATUS"
    }
    
    # Freshness rules in hours (None = never expires)
    FRESHNESS_HOURS = {
        0: None,           # TIMELESS - never expires
        1: None,           # HISTORICAL - never expires
        2: 7 * 24,         # BREAKING_NEWS - 7 days
        3: 24,             # ONGOING - 24 hours
        4: None,           # PREDICTION - uses explicit expires_at
        5: 30 * 24,        # STATUS - 30 days
    }


class ClaimMetadata(TypedDict):
    """Processed claim metadata for on-chain storage."""
    original_claim: str
    normalized_claim: str
    claim_hash: str           # SHA256 hash of normalized claim
    claim_signature: str      # Semantic signature (keywords hash)
    keywords: list[str]       # Extracted keywords for search
    claim_type: int           # 0-5 (ClaimType enum)
    claim_type_name: str      # Human readable type name
    timestamp: int            # Unix timestamp
    expires_at: int           # Unix timestamp (0 = never)
    freshness_hours: int      # Max age in hours (0 = never expires)


# ============ Core Functions ============

def normalize_claim(claim: str) -> str:
    """
    Normalize claim text for consistent hashing.
    - Lowercase
    - Remove extra whitespace
    - Remove punctuation except essential ones
    - Strip leading/trailing whitespace
    """
    # Lowercase
    normalized = claim.lower()
    
    # Replace multiple whitespace with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove non-essential punctuation but keep numbers and letters
    normalized = re.sub(r'[^\w\s\.\,\?\!\$\%]', '', normalized)
    
    # Strip whitespace
    normalized = normalized.strip()
    
    return normalized


def generate_claim_hash(claim: str) -> str:
    """
    Generate SHA256 hash of normalized claim.
    Used for exact match lookups.
    """
    normalized = normalize_claim(claim)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def extract_keywords(claim: str) -> list[str]:
    """
    Extract searchable keywords from claim using LLM.
    Returns 3-5 key terms for semantic search.
    """
    prompt = f"""Extract 3-5 key search terms from this claim.
Return ONLY lowercase words separated by commas, no explanations.

Claim: "{claim}"

Rules:
- Include named entities (people, companies, places)
- Include key actions/events (acquired, announced, crashed)
- Include important numbers/dates if present
- No stop words (the, is, a, an)

Example output: tesla, twitter, acquisition, 100b, 2025"""

    try:
        response = llm.invoke([
            SystemMessage(content="You extract keywords. Return only comma-separated words."),
            HumanMessage(content=prompt)
        ])
        
        # Parse response
        keywords = [k.strip().lower() for k in response.content.split(",")]
        
        # Filter empty strings and limit to 5
        keywords = [k for k in keywords if k and len(k) > 1][:5]
        
        return keywords if keywords else ["unknown"]
        
    except Exception as e:
        # Fallback: simple word extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', claim.lower())
        # Remove common stop words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'her', 'was', 'one', 'our', 'out', 'his', 'have', 'been', 'were', 'they', 'this', 'that', 'with', 'from'}
        return [w for w in words if w not in stop_words][:5]


def generate_claim_signature(keywords: list[str]) -> str:
    """
    Generate semantic signature from keywords.
    Used for finding similar claims (deduplication).
    """
    # Sort keywords for consistent ordering
    sorted_keywords = sorted(set(keywords))
    
    # Join and hash
    signature_input = "_".join(sorted_keywords)
    return hashlib.sha256(signature_input.encode('utf-8')).hexdigest()


def detect_claim_type(claim: str) -> int:
    """
    Detect claim type using LLM for freshness rules.
    Returns ClaimType constant (0-5).
    """
    prompt = f"""Classify this claim into ONE category:

CLAIM: "{claim}"

Categories:
0 = TIMELESS (scientific facts, math, definitions, universal truths)
1 = HISTORICAL (past events with specific dates, completed actions)
2 = BREAKING_NEWS (recent events, announcements, news within days/weeks)
3 = ONGOING (current prices, live situations, "right now" states)
4 = PREDICTION (future events, forecasts, "will happen")
5 = STATUS (current roles, positions, ownership, company states)

Return ONLY a single number (0-5), nothing else."""

    try:
        response = llm.invoke([
            SystemMessage(content="You classify claims. Return only a number 0-5."),
            HumanMessage(content=prompt)
        ])
        
        # Extract number from response
        match = re.search(r'\d', response.content)
        if match:
            claim_type = int(match.group())
            if 0 <= claim_type <= 5:
                return claim_type
        
        # Default to BREAKING_NEWS if parsing fails
        return ClaimType.BREAKING_NEWS
        
    except Exception:
        return ClaimType.BREAKING_NEWS


def calculate_expiry(claim_type: int, timestamp: int = None) -> int:
    """
    Calculate expiry timestamp based on claim type.
    
    Args:
        claim_type: ClaimType constant (0-5)
        timestamp: Base timestamp (default: now)
    
    Returns:
        Unix timestamp for expiry (0 = never expires)
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    freshness_hours = ClaimType.FRESHNESS_HOURS.get(claim_type)
    
    if freshness_hours is None:
        return 0  # Never expires
    
    # Calculate expiry
    expiry_seconds = freshness_hours * 3600
    return timestamp + expiry_seconds


def is_verdict_fresh(timestamp: int, expires_at: int, claim_type: int = None) -> dict:
    """
    Check if a verdict is still fresh/valid.
    
    Returns:
        dict with freshness info
    """
    now = int(time.time())
    age_seconds = now - timestamp
    age_hours = age_seconds / 3600
    age_days = age_hours / 24
    
    # Check explicit expiry first
    if expires_at > 0 and now > expires_at:
        return {
            "is_fresh": False,
            "age_hours": round(age_hours, 1),
            "age_days": round(age_days, 1),
            "freshness_score": 0.0,
            "recommendation": "EXPIRED - Re-verify required",
            "expired": True
        }
    
    # Get freshness rule for claim type
    if claim_type is not None:
        max_age_hours = ClaimType.FRESHNESS_HOURS.get(claim_type)
    else:
        max_age_hours = ClaimType.FRESHNESS_HOURS[ClaimType.BREAKING_NEWS]  # Default
    
    # Calculate freshness score
    if max_age_hours is None:
        # Never expires
        return {
            "is_fresh": True,
            "age_hours": round(age_hours, 1),
            "age_days": round(age_days, 1),
            "freshness_score": 1.0,
            "recommendation": "TIMELESS - Always valid",
            "expired": False
        }
    
    freshness_score = max(0.0, 1.0 - (age_hours / max_age_hours))
    is_fresh = age_hours < max_age_hours
    
    if freshness_score >= 0.8:
        recommendation = "VERY FRESH - High confidence"
    elif freshness_score >= 0.5:
        recommendation = "FRESH - Good confidence"
    elif freshness_score >= 0.2:
        recommendation = "AGING - Consider re-verification"
    else:
        recommendation = "STALE - Re-verify recommended"
    
    return {
        "is_fresh": is_fresh,
        "age_hours": round(age_hours, 1),
        "age_days": round(age_days, 1),
        "freshness_score": round(freshness_score, 2),
        "recommendation": recommendation,
        "expired": not is_fresh
    }


# ============ Main Processor Class ============

class ClaimProcessor:
    """
    Processes claims for on-chain storage preparation.
    
    Extracts:
    - claim_hash: For exact matching
    - keywords: For semantic search
    - claim_type: For freshness rules
    - expires_at: Based on claim type
    """
    
    def process(self, claim: str) -> ClaimMetadata:
        """
        Process a claim and extract all metadata.
        
        Args:
            claim: Original claim text
            
        Returns:
            ClaimMetadata with all extracted fields
        """
        # Normalize claim
        normalized = normalize_claim(claim)
        
        # Generate hashes
        claim_hash = generate_claim_hash(claim)
        
        # Extract keywords
        keywords = extract_keywords(claim)
        
        # Generate signature from keywords
        claim_signature = generate_claim_signature(keywords)
        
        # Detect claim type
        claim_type = detect_claim_type(claim)
        claim_type_name = ClaimType.NAMES.get(claim_type, "UNKNOWN")
        
        # Calculate timestamps
        timestamp = int(time.time())
        expires_at = calculate_expiry(claim_type, timestamp)
        freshness_hours = ClaimType.FRESHNESS_HOURS.get(claim_type) or 0
        
        return ClaimMetadata(
            original_claim=claim,
            normalized_claim=normalized,
            claim_hash=claim_hash,
            claim_signature=claim_signature,
            keywords=keywords,
            claim_type=claim_type,
            claim_type_name=claim_type_name,
            timestamp=timestamp,
            expires_at=expires_at,
            freshness_hours=freshness_hours
        )
    
    def format_expiry(self, expires_at: int) -> str:
        """Format expiry timestamp for display."""
        if expires_at == 0:
            return "Never"
        
        expiry_date = datetime.fromtimestamp(expires_at)
        return expiry_date.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_freshness_label(self, claim_type: int) -> str:
        """Get human-readable freshness label."""
        hours = ClaimType.FRESHNESS_HOURS.get(claim_type)
        if hours is None:
            return "Never expires"
        elif hours <= 24:
            return f"{hours} hours"
        else:
            days = hours // 24
            return f"{days} days"
