"""
DOW Data Models - Aletheia

Data models for the Decentralized Oracle of Wisdom challenge system.
Users stake SOL to challenge AI verdicts, community votes to resolve.
"""

import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any


# ==================== ENUMS ====================

class ChallengeStatus(Enum):
    """Challenge lifecycle status."""
    PENDING = "pending"              # Just submitted, waiting for voting to start
    VOTING = "voting"                # Community voting in progress
    RESOLVED_AI_WIN = "ai_win"       # AI was correct, challenger loses stake
    RESOLVED_USER_WIN = "user_win"   # Challenger was correct, gets 2x stake
    CANCELLED = "cancelled"          # Insufficient votes, stake refunded
    DISPUTED = "disputed"            # Under admin review


class VotePosition(Enum):
    """Vote positions."""
    AI_CORRECT = "ai"                # Voter believes AI verdict is correct
    CHALLENGER_CORRECT = "challenger" # Voter believes challenger is correct


# ==================== CONFIG ====================

@dataclass
class ChallengeConfig:
    """Configuration for the challenge system."""
    # Stake limits
    min_stake: float = 1.0           # Minimum SOL to challenge
    max_stake: float = 100.0         # Maximum SOL to challenge
    
    # Timing (in hours)
    challenge_window: int = 72       # Hours after verdict to allow challenges
    voting_period: int = 48          # Hours for community voting
    
    # Voting requirements
    min_voters: int = 50             # Minimum votes for valid resolution
    min_voter_reputation: int = 5    # Minimum reputation to vote
    
    # Evidence requirements
    min_evidence_links: int = 2      # Minimum sources required
    min_explanation_length: int = 100 # Minimum chars for explanation
    
    # Payouts
    winner_multiplier: float = 2.0   # Challenger gets 2x stake if wins
    voter_reward: float = 0.01       # SOL reward for correct voters
    
    # Anti-spam
    max_active_challenges_per_user: int = 3


# ==================== ID GENERATORS ====================

def generate_challenge_id() -> str:
    """Generate unique challenge ID."""
    return f"chl_{uuid.uuid4().hex[:12]}"


def generate_vote_id() -> str:
    """Generate unique vote ID."""
    return f"vot_{uuid.uuid4().hex[:12]}"


# ==================== DATA MODELS ====================

@dataclass
class VoterInfo:
    """Information about a voter for weight calculation."""
    wallet_address: str
    reputation: int = 0
    historical_accuracy: float = 0.5  # % of correct votes
    domain_expertise: List[str] = field(default_factory=list)
    wallet_age_days: int = 0
    total_votes: int = 0
    
    def calculate_vote_weight(self, claim_domain: str = "") -> float:
        """
        Calculate weighted vote value.
        
        Weight = 1 (base) 
               + sqrt(reputation) / 10 
               + 0.5 (if domain expert)
               + 0.2 (if >80% accuracy)
        """
        import math
        
        weight = 1.0
        
        # Reputation bonus
        if self.reputation > 0:
            weight += math.sqrt(self.reputation) / 10
        
        # Domain expertise bonus
        if claim_domain and claim_domain.lower() in [d.lower() for d in self.domain_expertise]:
            weight += 0.5
        
        # Historical accuracy bonus
        if self.total_votes >= 10 and self.historical_accuracy > 0.8:
            weight += 0.2
        
        return round(weight, 3)
    
    def to_dict(self) -> Dict:
        return {
            "wallet_address": self.wallet_address,
            "reputation": self.reputation,
            "historical_accuracy": self.historical_accuracy,
            "domain_expertise": self.domain_expertise,
            "wallet_age_days": self.wallet_age_days,
            "total_votes": self.total_votes
        }


@dataclass
class Vote:
    """Individual vote on a challenge."""
    vote_id: str
    challenge_id: str
    voter_wallet: str
    position: VotePosition
    weight: float              # Calculated vote weight
    reasoning: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "vote_id": self.vote_id,
            "challenge_id": self.challenge_id,
            "voter_wallet": self.voter_wallet,
            "position": self.position.value,
            "weight": self.weight,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }


@dataclass
class Challenge:
    """A challenge to an AI verdict."""
    challenge_id: str
    
    # Original verdict info
    verdict_id: str
    claim: str
    claim_domain: str
    original_verdict: str       # "TRUE", "FALSE", "UNCERTAIN"
    original_confidence: float
    
    # Challenger info
    challenger_wallet: str
    stake_amount: float         # in SOL
    
    # Evidence provided by challenger
    evidence_links: List[str]
    explanation: str
    
    # Timing
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    voting_starts_at: str = ""
    voting_ends_at: str = ""
    resolved_at: Optional[str] = None
    
    # Status
    status: ChallengeStatus = ChallengeStatus.PENDING
    
    # Voting tallies (weighted)
    votes_for_ai: float = 0.0
    votes_for_challenger: float = 0.0
    voter_count: int = 0
    vote_ids: List[str] = field(default_factory=list)
    
    # Resolution
    winner: Optional[str] = None  # "ai" or "challenger"
    payout_amount: Optional[float] = None
    resolution_reason: Optional[str] = None
    
    def __post_init__(self):
        if not self.voting_starts_at:
            self.voting_starts_at = datetime.now().isoformat()
        if not self.voting_ends_at:
            voting_end = datetime.now() + timedelta(hours=48)
            self.voting_ends_at = voting_end.isoformat()
    
    @property
    def is_voting_open(self) -> bool:
        """Check if voting is currently open."""
        now = datetime.now()
        start = datetime.fromisoformat(self.voting_starts_at)
        end = datetime.fromisoformat(self.voting_ends_at)
        return start <= now <= end and self.status == ChallengeStatus.VOTING
    
    @property
    def ai_vote_percentage(self) -> float:
        """Percentage of votes for AI."""
        total = self.votes_for_ai + self.votes_for_challenger
        if total == 0:
            return 50.0
        return round((self.votes_for_ai / total) * 100, 1)
    
    @property
    def challenger_vote_percentage(self) -> float:
        """Percentage of votes for challenger."""
        return round(100 - self.ai_vote_percentage, 1)
    
    @property
    def time_remaining(self) -> Optional[timedelta]:
        """Time remaining for voting."""
        if self.status != ChallengeStatus.VOTING:
            return None
        end = datetime.fromisoformat(self.voting_ends_at)
        remaining = end - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def to_dict(self) -> Dict:
        return {
            "challenge_id": self.challenge_id,
            "verdict_id": self.verdict_id,
            "claim": self.claim,
            "claim_domain": self.claim_domain,
            "original_verdict": self.original_verdict,
            "original_confidence": self.original_confidence,
            "challenger_wallet": self.challenger_wallet,
            "stake_amount": self.stake_amount,
            "evidence_links": self.evidence_links,
            "explanation": self.explanation,
            "created_at": self.created_at,
            "voting_starts_at": self.voting_starts_at,
            "voting_ends_at": self.voting_ends_at,
            "resolved_at": self.resolved_at,
            "status": self.status.value,
            "votes_for_ai": self.votes_for_ai,
            "votes_for_challenger": self.votes_for_challenger,
            "voter_count": self.voter_count,
            "ai_vote_percentage": self.ai_vote_percentage,
            "challenger_vote_percentage": self.challenger_vote_percentage,
            "winner": self.winner,
            "payout_amount": self.payout_amount,
            "resolution_reason": self.resolution_reason,
            "is_voting_open": self.is_voting_open,
            "time_remaining_seconds": self.time_remaining.total_seconds() if self.time_remaining else None
        }


@dataclass
class Treasury:
    """Aletheia's resource fund for paying challenge winners."""
    total_balance: float = 1000.0     # Starting SOL balance
    reserved_for_payouts: float = 0.0  # Locked for pending challenges
    
    # Stats
    total_challenges_received: int = 0
    challenges_won_by_ai: int = 0
    challenges_won_by_users: int = 0
    total_earned_from_wins: float = 0.0
    total_paid_to_winners: float = 0.0
    
    @property
    def available_balance(self) -> float:
        """Balance available for new challenge reserves."""
        return self.total_balance - self.reserved_for_payouts
    
    @property
    def ai_win_rate(self) -> float:
        """Percentage of challenges won by AI."""
        total = self.challenges_won_by_ai + self.challenges_won_by_users
        if total == 0:
            return 100.0
        return round((self.challenges_won_by_ai / total) * 100, 2)
    
    @property
    def net_profit(self) -> float:
        """Net profit/loss from challenges."""
        return self.total_earned_from_wins - self.total_paid_to_winners
    
    def reserve_for_challenge(self, stake_amount: float, multiplier: float = 2.0) -> bool:
        """
        Reserve funds for a potential payout if challenger wins.
        Returns False if insufficient funds.
        """
        # If challenger wins, we pay their stake * multiplier
        # But we also get their stake, so net payout is stake * (multiplier - 1)
        potential_payout = stake_amount * (multiplier - 1)
        
        if potential_payout > self.available_balance:
            return False
        
        self.reserved_for_payouts += potential_payout
        return True
    
    def release_reservation(self, stake_amount: float, multiplier: float = 2.0):
        """Release reserved funds (when challenge is resolved or cancelled)."""
        potential_payout = stake_amount * (multiplier - 1)
        self.reserved_for_payouts = max(0, self.reserved_for_payouts - potential_payout)
    
    def process_ai_win(self, stake_amount: float):
        """Process when AI wins a challenge."""
        self.release_reservation(stake_amount)
        self.total_balance += stake_amount  # We keep challenger's stake
        self.total_earned_from_wins += stake_amount
        self.challenges_won_by_ai += 1
        self.total_challenges_received += 1
    
    def process_user_win(self, stake_amount: float, multiplier: float = 2.0):
        """Process when challenger wins."""
        self.release_reservation(stake_amount)
        payout = stake_amount * multiplier
        our_contribution = stake_amount * (multiplier - 1)
        self.total_balance -= our_contribution  # We contribute the extra
        self.total_paid_to_winners += our_contribution
        self.challenges_won_by_users += 1
        self.total_challenges_received += 1
        return payout
    
    def to_dict(self) -> Dict:
        return {
            "total_balance": round(self.total_balance, 4),
            "reserved_for_payouts": round(self.reserved_for_payouts, 4),
            "available_balance": round(self.available_balance, 4),
            "total_challenges_received": self.total_challenges_received,
            "challenges_won_by_ai": self.challenges_won_by_ai,
            "challenges_won_by_users": self.challenges_won_by_users,
            "ai_win_rate": self.ai_win_rate,
            "total_earned_from_wins": round(self.total_earned_from_wins, 4),
            "total_paid_to_winners": round(self.total_paid_to_winners, 4),
            "net_profit": round(self.net_profit, 4)
        }
