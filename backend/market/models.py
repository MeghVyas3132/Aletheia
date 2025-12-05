"""
Truth Market Models - Aletheia V2

Data models for the prediction market system.
Users bet on whether Aletheia's verdict is correct.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid
import hashlib


class MarketStatus(Enum):
    """Market lifecycle status."""
    PENDING = "pending"          # Waiting for Aletheia verdict
    OPEN = "open"                # Accepting bets
    CLOSED = "closed"            # No more bets, awaiting resolution
    RESOLVED = "resolved"        # Outcome determined, payouts available
    DISPUTED = "disputed"        # Under dispute review
    VOIDED = "voided"            # Market cancelled, bets refunded


class BetPosition(Enum):
    """Bet positions."""
    CORRECT = "correct"  # Betting Aletheia is correct
    WRONG = "wrong"      # Betting Aletheia is wrong


class ResolutionOutcome(Enum):
    """How the market was resolved."""
    ALETHEIA_CORRECT = "aletheia_correct"
    ALETHEIA_WRONG = "aletheia_wrong"
    VOIDED = "voided"


@dataclass
class User:
    """User account for the Truth Market."""
    user_id: str
    username: str
    balance: float  # ALETH tokens
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def win_rate(self) -> float:
        """Calculate user's win rate."""
        if self.total_bets == 0:
            return 0.0
        return self.wins / self.total_bets
    
    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "balance": self.balance,
            "total_bets": self.total_bets,
            "wins": self.wins,
            "losses": self.losses,
            "total_profit": self.total_profit,
            "win_rate": self.win_rate,
            "created_at": self.created_at
        }


@dataclass
class Bet:
    """Individual bet placed by a user."""
    bet_id: str
    user_id: str
    market_id: str
    position: BetPosition  # CORRECT or WRONG
    amount: float  # ALETH tokens bet
    odds_at_bet: float  # Odds when bet was placed
    potential_payout: float  # What they'd win
    placed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active, won, lost, refunded
    payout: float = 0.0  # Actual payout received
    
    def to_dict(self) -> Dict:
        return {
            "bet_id": self.bet_id,
            "user_id": self.user_id,
            "market_id": self.market_id,
            "position": self.position.value,
            "amount": self.amount,
            "odds_at_bet": self.odds_at_bet,
            "potential_payout": self.potential_payout,
            "placed_at": self.placed_at,
            "status": self.status,
            "payout": self.payout
        }


@dataclass
class Market:
    """A prediction market for a single claim."""
    market_id: str
    claim: str
    claim_hash: str
    
    # Aletheia's verdict
    aletheia_verdict: str  # "TRUE", "FALSE", "UNCERTAIN"
    aletheia_confidence: float  # 0.0-1.0
    verdict_summary: str
    
    # Market details
    category: str  # "tech", "politics", "finance", etc.
    status: MarketStatus = MarketStatus.OPEN
    
    # Betting pools
    correct_pool: float = 0.0  # Total bet on "Aletheia Correct"
    wrong_pool: float = 0.0    # Total bet on "Aletheia Wrong"
    
    # Timing
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    closes_at: str = ""  # When betting closes
    resolved_at: str = ""  # When outcome was determined
    
    # Resolution
    resolution: Optional[ResolutionOutcome] = None
    resolution_source: str = ""  # Where the resolution came from
    resolution_evidence: str = ""  # Evidence for resolution
    
    # Stats
    total_bettors: int = 0
    bets: List[str] = field(default_factory=list)  # List of bet IDs
    
    def __post_init__(self):
        if not self.closes_at:
            # Default: market closes in 7 days
            close_time = datetime.now() + timedelta(days=7)
            self.closes_at = close_time.isoformat()
    
    @property
    def total_pool(self) -> float:
        """Total tokens in the market."""
        return self.correct_pool + self.wrong_pool
    
    @property
    def correct_odds(self) -> float:
        """Probability implied by betting for 'correct'."""
        if self.total_pool == 0:
            return 0.5
        return self.correct_pool / self.total_pool
    
    @property
    def wrong_odds(self) -> float:
        """Probability implied by betting for 'wrong'."""
        if self.total_pool == 0:
            return 0.5
        return self.wrong_pool / self.total_pool
    
    @property
    def correct_payout_multiplier(self) -> float:
        """How much you win per token if betting 'correct'."""
        if self.correct_pool == 0:
            return 10.0  # High payout for first bet
        return self.total_pool / self.correct_pool
    
    @property
    def wrong_payout_multiplier(self) -> float:
        """How much you win per token if betting 'wrong'."""
        if self.wrong_pool == 0:
            return 10.0  # High payout for first bet
        return self.total_pool / self.wrong_pool
    
    def is_open(self) -> bool:
        """Check if market is accepting bets."""
        if self.status != MarketStatus.OPEN:
            return False
        if datetime.fromisoformat(self.closes_at) < datetime.now():
            return False
        return True
    
    def time_remaining(self) -> str:
        """Human-readable time until market closes."""
        if not self.is_open():
            return "Closed"
        
        remaining = datetime.fromisoformat(self.closes_at) - datetime.now()
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def to_dict(self) -> Dict:
        return {
            "market_id": self.market_id,
            "claim": self.claim,
            "claim_hash": self.claim_hash,
            "aletheia_verdict": self.aletheia_verdict,
            "aletheia_confidence": self.aletheia_confidence,
            "verdict_summary": self.verdict_summary,
            "category": self.category,
            "status": self.status.value,
            "correct_pool": self.correct_pool,
            "wrong_pool": self.wrong_pool,
            "total_pool": self.total_pool,
            "correct_odds": self.correct_odds,
            "wrong_odds": self.wrong_odds,
            "correct_payout_multiplier": self.correct_payout_multiplier,
            "wrong_payout_multiplier": self.wrong_payout_multiplier,
            "created_at": self.created_at,
            "closes_at": self.closes_at,
            "time_remaining": self.time_remaining(),
            "total_bettors": self.total_bettors,
            "is_open": self.is_open(),
            "resolution": self.resolution.value if self.resolution else None,
            "resolution_source": self.resolution_source,
            "resolved_at": self.resolved_at
        }


@dataclass
class LeaderboardEntry:
    """Entry in the leaderboard."""
    rank: int
    user_id: str
    username: str
    win_rate: float
    total_profit: float
    total_bets: int
    current_streak: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "rank": self.rank,
            "user_id": self.user_id,
            "username": self.username,
            "win_rate": self.win_rate,
            "total_profit": self.total_profit,
            "total_bets": self.total_bets,
            "current_streak": self.current_streak
        }


# Fee structure
class Fees:
    """Platform fee structure."""
    GAS_FEE = 0.5  # ALETH per transaction
    PLATFORM_FEE_PERCENT = 0.02  # 2% of winnings
    EARLY_CASHOUT_PENALTY = 0.05  # 5% penalty
    MARKET_CREATION_FEE = 10.0  # ALETH to create market (refunded on resolution)
    DISPUTE_STAKE = 50.0  # ALETH to dispute (slashed if wrong)


def generate_market_id() -> str:
    """Generate unique market ID."""
    return f"MKT_{uuid.uuid4().hex[:12].upper()}"


def generate_bet_id() -> str:
    """Generate unique bet ID."""
    return f"BET_{uuid.uuid4().hex[:12].upper()}"


def generate_user_id() -> str:
    """Generate unique user ID."""
    return f"USR_{uuid.uuid4().hex[:12].upper()}"


def hash_claim(claim: str) -> str:
    """Generate hash of claim for deduplication."""
    normalized = claim.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
