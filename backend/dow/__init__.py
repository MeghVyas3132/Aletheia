"""
Decentralized Oracle of Wisdom (DOW) - Aletheia

Challenge system where users can stake tokens to dispute AI verdicts.
Community votes determine the winner.

Now with SQLite persistence!
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

# Use the new V2 manager with SQLite persistence
from dow.manager_v2 import (
    DOWManagerV2 as DOWManager,
    get_dow_manager
)

from dow import database

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
