"""
DOW Manager - Aletheia

Core operations for the Decentralized Oracle of Wisdom:
- Submit challenges
- Cast votes
- Resolve challenges
- Manage treasury
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dow.models import (
    Challenge, ChallengeStatus,
    Vote, VotePosition, VoterInfo,
    Treasury, ChallengeConfig,
    generate_challenge_id, generate_vote_id
)

logger = logging.getLogger(__name__)


class DOWManager:
    """
    Manages the Decentralized Oracle of Wisdom challenge system.
    
    In production, this would integrate with Solana for real token transactions.
    Currently uses in-memory storage for demonstration.
    """
    
    def __init__(self, config: ChallengeConfig = None, storage_path: str = None):
        self.config = config or ChallengeConfig()
        self.storage_path = storage_path or "dow_data.json"
        
        # In-memory storage
        self.challenges: Dict[str, Challenge] = {}
        self.votes: Dict[str, Vote] = {}
        self.voters: Dict[str, VoterInfo] = {}
        self.treasury: Treasury = Treasury()
        
        # Verdict tracking (would come from main API in production)
        self.verdicts: Dict[str, Dict] = {}
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load data from storage file."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    # Reconstruct objects (simplified)
                    logger.info(f"Loaded DOW data from {self.storage_path}")
        except Exception as e:
            logger.warning(f"Could not load DOW data: {e}")
    
    def _save_data(self):
        """Save data to storage file."""
        try:
            data = {
                "challenges": {k: v.to_dict() for k, v in self.challenges.items()},
                "treasury": self.treasury.to_dict(),
                "voters": {k: v.to_dict() for k, v in self.voters.items()}
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save DOW data: {e}")
    
    # ==================== VERDICT TRACKING ====================
    
    def register_verdict(
        self,
        verdict_id: str,
        claim: str,
        domain: str,
        verdict: str,
        confidence: float
    ):
        """Register a verdict that can be challenged."""
        self.verdicts[verdict_id] = {
            "verdict_id": verdict_id,
            "claim": claim,
            "domain": domain,
            "verdict": verdict,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
            "challenge_deadline": (datetime.now() + timedelta(hours=self.config.challenge_window)).isoformat()
        }
        logger.info(f"Registered verdict {verdict_id} for potential challenges")
    
    def get_verdict(self, verdict_id: str) -> Optional[Dict]:
        """Get verdict info."""
        return self.verdicts.get(verdict_id)
    
    def is_verdict_challengeable(self, verdict_id: str) -> Tuple[bool, str]:
        """Check if a verdict can still be challenged."""
        verdict = self.verdicts.get(verdict_id)
        if not verdict:
            return False, "Verdict not found"
        
        deadline = datetime.fromisoformat(verdict["challenge_deadline"])
        if datetime.now() > deadline:
            return False, "Challenge window has expired"
        
        # Check if already has an active challenge
        for challenge in self.challenges.values():
            if challenge.verdict_id == verdict_id and challenge.status in (
                ChallengeStatus.PENDING, ChallengeStatus.VOTING
            ):
                return False, "Verdict already has an active challenge"
        
        return True, "OK"
    
    # ==================== VOTER MANAGEMENT ====================
    
    def get_or_create_voter(self, wallet_address: str) -> VoterInfo:
        """Get existing voter or create new one."""
        if wallet_address not in self.voters:
            self.voters[wallet_address] = VoterInfo(
                wallet_address=wallet_address,
                reputation=10,  # Starting reputation
                wallet_age_days=30  # Assume valid for demo
            )
        return self.voters[wallet_address]
    
    def update_voter_reputation(self, wallet_address: str, delta: int):
        """Update voter's reputation."""
        voter = self.get_or_create_voter(wallet_address)
        voter.reputation = max(0, voter.reputation + delta)
        self._save_data()
    
    # ==================== CHALLENGE OPERATIONS ====================
    
    def submit_challenge(
        self,
        verdict_id: str,
        challenger_wallet: str,
        stake_amount: float,
        evidence_links: List[str],
        explanation: str
    ) -> Tuple[bool, str, Optional[Challenge]]:
        """
        Submit a new challenge to a verdict.
        
        Returns: (success, message, challenge)
        """
        # Validate verdict
        can_challenge, reason = self.is_verdict_challengeable(verdict_id)
        if not can_challenge:
            return False, reason, None
        
        verdict = self.verdicts[verdict_id]
        
        # Validate stake amount
        if stake_amount < self.config.min_stake:
            return False, f"Minimum stake is {self.config.min_stake} SOL", None
        if stake_amount > self.config.max_stake:
            return False, f"Maximum stake is {self.config.max_stake} SOL", None
        
        # Validate evidence
        if len(evidence_links) < self.config.min_evidence_links:
            return False, f"Minimum {self.config.min_evidence_links} evidence links required", None
        if len(explanation) < self.config.min_explanation_length:
            return False, f"Explanation must be at least {self.config.min_explanation_length} characters", None
        
        # Check user's active challenges
        active_challenges = sum(
            1 for c in self.challenges.values()
            if c.challenger_wallet == challenger_wallet 
            and c.status in (ChallengeStatus.PENDING, ChallengeStatus.VOTING)
        )
        if active_challenges >= self.config.max_active_challenges_per_user:
            return False, f"Maximum {self.config.max_active_challenges_per_user} active challenges allowed", None
        
        # Reserve treasury funds for potential payout
        if not self.treasury.reserve_for_challenge(stake_amount, self.config.winner_multiplier):
            return False, "Insufficient treasury funds to back this challenge", None
        
        # Create challenge
        challenge = Challenge(
            challenge_id=generate_challenge_id(),
            verdict_id=verdict_id,
            claim=verdict["claim"],
            claim_domain=verdict["domain"],
            original_verdict=verdict["verdict"],
            original_confidence=verdict["confidence"],
            challenger_wallet=challenger_wallet,
            stake_amount=stake_amount,
            evidence_links=evidence_links,
            explanation=explanation,
            status=ChallengeStatus.VOTING  # Start voting immediately
        )
        
        self.challenges[challenge.challenge_id] = challenge
        self._save_data()
        
        logger.info(f"Challenge {challenge.challenge_id} submitted by {challenger_wallet} with {stake_amount} SOL")
        
        return True, "Challenge submitted successfully", challenge
    
    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get challenge by ID."""
        return self.challenges.get(challenge_id)
    
    def get_active_challenges(self) -> List[Challenge]:
        """Get all active challenges (voting in progress)."""
        return [
            c for c in self.challenges.values()
            if c.status == ChallengeStatus.VOTING
        ]
    
    def get_challenges_by_wallet(self, wallet_address: str) -> List[Challenge]:
        """Get all challenges by a specific wallet."""
        return [
            c for c in self.challenges.values()
            if c.challenger_wallet == wallet_address
        ]
    
    # ==================== VOTING OPERATIONS ====================
    
    def cast_vote(
        self,
        challenge_id: str,
        voter_wallet: str,
        position: str,  # "ai" or "challenger"
        reasoning: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Vote]]:
        """
        Cast a vote on a challenge.
        
        Returns: (success, message, vote)
        """
        challenge = self.challenges.get(challenge_id)
        if not challenge:
            return False, "Challenge not found", None
        
        if challenge.status != ChallengeStatus.VOTING:
            return False, "Voting is not open for this challenge", None
        
        if not challenge.is_voting_open:
            return False, "Voting period has ended", None
        
        # Check if already voted
        for vote_id in challenge.vote_ids:
            vote = self.votes.get(vote_id)
            if vote and vote.voter_wallet == voter_wallet:
                return False, "You have already voted on this challenge", None
        
        # Validate voter
        voter = self.get_or_create_voter(voter_wallet)
        if voter.reputation < self.config.min_voter_reputation:
            return False, f"Minimum {self.config.min_voter_reputation} reputation required to vote", None
        
        # Can't vote on own challenge
        if voter_wallet == challenge.challenger_wallet:
            return False, "Cannot vote on your own challenge", None
        
        # Parse position
        try:
            vote_position = VotePosition.AI_CORRECT if position == "ai" else VotePosition.CHALLENGER_CORRECT
        except:
            return False, "Invalid position. Use 'ai' or 'challenger'", None
        
        # Calculate vote weight
        weight = voter.calculate_vote_weight(challenge.claim_domain)
        
        # Create vote
        vote = Vote(
            vote_id=generate_vote_id(),
            challenge_id=challenge_id,
            voter_wallet=voter_wallet,
            position=vote_position,
            weight=weight,
            reasoning=reasoning
        )
        
        # Update challenge tallies
        if vote_position == VotePosition.AI_CORRECT:
            challenge.votes_for_ai += weight
        else:
            challenge.votes_for_challenger += weight
        
        challenge.voter_count += 1
        challenge.vote_ids.append(vote.vote_id)
        
        self.votes[vote.vote_id] = vote
        voter.total_votes += 1
        
        self._save_data()
        
        logger.info(f"Vote {vote.vote_id} cast by {voter_wallet} for {position} (weight: {weight})")
        
        return True, "Vote cast successfully", vote
    
    def get_votes_for_challenge(self, challenge_id: str) -> List[Vote]:
        """Get all votes for a challenge."""
        challenge = self.challenges.get(challenge_id)
        if not challenge:
            return []
        
        return [
            self.votes[vote_id] 
            for vote_id in challenge.vote_ids 
            if vote_id in self.votes
        ]
    
    # ==================== RESOLUTION ====================
    
    def check_and_resolve_challenges(self) -> List[Tuple[str, str]]:
        """
        Check all challenges and resolve those whose voting has ended.
        
        Returns: List of (challenge_id, outcome) tuples
        """
        resolved = []
        
        for challenge in list(self.challenges.values()):
            if challenge.status != ChallengeStatus.VOTING:
                continue
            
            # Check if voting period ended
            voting_end = datetime.fromisoformat(challenge.voting_ends_at)
            if datetime.now() < voting_end:
                continue
            
            # Resolve
            outcome = self._resolve_challenge(challenge)
            resolved.append((challenge.challenge_id, outcome))
        
        return resolved
    
    def _resolve_challenge(self, challenge: Challenge) -> str:
        """
        Resolve a single challenge based on votes.
        
        Returns: outcome string
        """
        # Check minimum voters
        if challenge.voter_count < self.config.min_voters:
            # Cancel and refund
            challenge.status = ChallengeStatus.CANCELLED
            challenge.resolution_reason = f"Insufficient votes ({challenge.voter_count}/{self.config.min_voters})"
            challenge.resolved_at = datetime.now().isoformat()
            
            # Release treasury reservation
            self.treasury.release_reservation(challenge.stake_amount, self.config.winner_multiplier)
            
            self._save_data()
            logger.info(f"Challenge {challenge.challenge_id} cancelled: insufficient votes")
            return "cancelled"
        
        # Determine winner
        if challenge.votes_for_ai > challenge.votes_for_challenger:
            # AI wins
            challenge.status = ChallengeStatus.RESOLVED_AI_WIN
            challenge.winner = "ai"
            challenge.resolution_reason = f"AI verdict upheld ({challenge.ai_vote_percentage}% support)"
            challenge.resolved_at = datetime.now().isoformat()
            
            # Process treasury
            self.treasury.process_ai_win(challenge.stake_amount)
            
            # Update voter reputations
            self._reward_voters(challenge, winning_position=VotePosition.AI_CORRECT)
            
            self._save_data()
            logger.info(f"Challenge {challenge.challenge_id} resolved: AI wins")
            return "ai_win"
        
        else:
            # Challenger wins
            challenge.status = ChallengeStatus.RESOLVED_USER_WIN
            challenge.winner = "challenger"
            challenge.payout_amount = self.treasury.process_user_win(
                challenge.stake_amount, 
                self.config.winner_multiplier
            )
            challenge.resolution_reason = f"Challenger proved correct ({challenge.challenger_vote_percentage}% support)"
            challenge.resolved_at = datetime.now().isoformat()
            
            # Update voter reputations
            self._reward_voters(challenge, winning_position=VotePosition.CHALLENGER_CORRECT)
            
            # Mark verdict as corrected
            if challenge.verdict_id in self.verdicts:
                self.verdicts[challenge.verdict_id]["corrected"] = True
                self.verdicts[challenge.verdict_id]["corrected_by"] = challenge.challenge_id
            
            self._save_data()
            logger.info(f"Challenge {challenge.challenge_id} resolved: Challenger wins, payout {challenge.payout_amount} SOL")
            return "user_win"
    
    def _reward_voters(self, challenge: Challenge, winning_position: VotePosition):
        """Reward voters who voted correctly."""
        for vote_id in challenge.vote_ids:
            vote = self.votes.get(vote_id)
            if not vote:
                continue
            
            voter = self.voters.get(vote.voter_wallet)
            if not voter:
                continue
            
            if vote.position == winning_position:
                # Correct vote: +2 reputation
                voter.reputation += 2
                # Update accuracy
                voter.historical_accuracy = (
                    (voter.historical_accuracy * (voter.total_votes - 1) + 1) / voter.total_votes
                )
            else:
                # Wrong vote: no penalty (to encourage participation)
                # But update accuracy
                voter.historical_accuracy = (
                    (voter.historical_accuracy * (voter.total_votes - 1) + 0) / voter.total_votes
                )
    
    def force_resolve(self, challenge_id: str, winner: str, reason: str) -> Tuple[bool, str]:
        """
        Admin force-resolve a challenge.
        
        Args:
            winner: "ai" or "challenger"
            reason: Explanation for the decision
        """
        challenge = self.challenges.get(challenge_id)
        if not challenge:
            return False, "Challenge not found"
        
        if challenge.status not in (ChallengeStatus.PENDING, ChallengeStatus.VOTING, ChallengeStatus.DISPUTED):
            return False, "Challenge cannot be resolved"
        
        if winner == "ai":
            challenge.status = ChallengeStatus.RESOLVED_AI_WIN
            challenge.winner = "ai"
            self.treasury.process_ai_win(challenge.stake_amount)
        elif winner == "challenger":
            challenge.status = ChallengeStatus.RESOLVED_USER_WIN
            challenge.winner = "challenger"
            challenge.payout_amount = self.treasury.process_user_win(
                challenge.stake_amount,
                self.config.winner_multiplier
            )
        else:
            return False, "Invalid winner. Use 'ai' or 'challenger'"
        
        challenge.resolution_reason = f"Admin decision: {reason}"
        challenge.resolved_at = datetime.now().isoformat()
        
        self._save_data()
        return True, f"Challenge resolved: {winner} wins"
    
    # ==================== TREASURY OPERATIONS ====================
    
    def get_treasury_stats(self) -> Dict:
        """Get treasury statistics."""
        return self.treasury.to_dict()
    
    def add_treasury_funds(self, amount: float):
        """Add funds to treasury (admin/funding)."""
        self.treasury.total_balance += amount
        self._save_data()
        logger.info(f"Added {amount} SOL to treasury")
    
    # ==================== LEADERBOARDS ====================
    
    def get_challenger_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top challengers by successful challenges."""
        challenger_stats = {}
        
        for challenge in self.challenges.values():
            wallet = challenge.challenger_wallet
            if wallet not in challenger_stats:
                challenger_stats[wallet] = {
                    "wallet": wallet,
                    "total_challenges": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_earned": 0.0,
                    "total_staked": 0.0
                }
            
            challenger_stats[wallet]["total_challenges"] += 1
            challenger_stats[wallet]["total_staked"] += challenge.stake_amount
            
            if challenge.status == ChallengeStatus.RESOLVED_USER_WIN:
                challenger_stats[wallet]["wins"] += 1
                challenger_stats[wallet]["total_earned"] += challenge.payout_amount or 0
            elif challenge.status == ChallengeStatus.RESOLVED_AI_WIN:
                challenger_stats[wallet]["losses"] += 1
        
        # Sort by wins, then by earnings
        leaderboard = sorted(
            challenger_stats.values(),
            key=lambda x: (x["wins"], x["total_earned"]),
            reverse=True
        )[:limit]
        
        return leaderboard
    
    def get_voter_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top voters by accuracy and reputation."""
        voter_list = [
            {
                "wallet": v.wallet_address,
                "reputation": v.reputation,
                "accuracy": round(v.historical_accuracy * 100, 1),
                "total_votes": v.total_votes,
                "expertise": v.domain_expertise
            }
            for v in self.voters.values()
            if v.total_votes >= 5  # Minimum votes to qualify
        ]
        
        # Sort by reputation, then accuracy
        leaderboard = sorted(
            voter_list,
            key=lambda x: (x["reputation"], x["accuracy"]),
            reverse=True
        )[:limit]
        
        return leaderboard


# Singleton instance
_dow_manager: Optional[DOWManager] = None


def get_dow_manager() -> DOWManager:
    """Get the singleton DOW manager instance."""
    global _dow_manager
    if _dow_manager is None:
        _dow_manager = DOWManager()
    return _dow_manager
