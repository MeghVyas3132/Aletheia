"""
Truth Market Module - Aletheia V2

Polymarket-style prediction market for AI fact-checking verdicts.
"""

from market.models import (
    Market, Bet, User,
    MarketStatus, BetPosition, ResolutionOutcome,
    LeaderboardEntry, Fees,
    generate_market_id, generate_bet_id, generate_user_id, hash_claim
)

from market.manager import TruthMarketManager, get_market_manager

__all__ = [
    # Models
    "Market",
    "Bet", 
    "User",
    "MarketStatus",
    "BetPosition",
    "ResolutionOutcome",
    "LeaderboardEntry",
    "Fees",
    
    # Utilities
    "generate_market_id",
    "generate_bet_id",
    "generate_user_id",
    "hash_claim",
    
    # Manager
    "TruthMarketManager",
    "get_market_manager"
]
