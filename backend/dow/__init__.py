"""
Decentralized Oracle of Wisdom (DOW) - Aletheia

Challenge system where users can stake tokens to dispute AI verdicts.
Community votes determine the winner.
"""

from dow.models import (
    Challenge, 
    ChallengeStatus,
    Vote,
    VoterInfo,
    Treasury,
    ChallengeConfig,
    generate_challenge_id,
    generate_vote_id
)

from dow.manager import (
    DOWManager,
    get_dow_manager
)

__all__ = [
    # Models
    "Challenge",
    "ChallengeStatus",
    "Vote",
    "VoterInfo",
    "Treasury",
    "ChallengeConfig",
    
    # Utilities
    "generate_challenge_id",
    "generate_vote_id",
    
    # Manager
    "DOWManager",
    "get_dow_manager"
]
