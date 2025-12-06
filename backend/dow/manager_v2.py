"""
DOW Manager V2 - With SQLite Persistence

Core operations for the Decentralized Oracle of Wisdom:
- Submit challenges
- Cast votes  
- Resolve challenges
- Manage treasury

Now with persistent SQLite storage instead of in-memory.
"""

import os
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from dow import database as db
from dow.models import ChallengeConfig

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class DOWManagerV2:
    """
    Manages the Decentralized Oracle of Wisdom challenge system.
    Uses SQLite for persistent storage.
    """
    
    def __init__(self, config: ChallengeConfig = None):
        self.config = config or ChallengeConfig()
        
        # Ensure database is initialized
        db.init_database()
        
        logger.info("DOW Manager V2 initialized with SQLite persistence")
    
    # ==================== VERDICT TRACKING ====================
    
    def register_verdict(
        self,
        verdict_id: str,
        claim: str,
        domain: str,
        verdict: str,
        confidence: float
    ) -> Dict[str, Any]:
        """Register a verdict that can be challenged."""
        verdict_data = {
            "verdict_id": verdict_id,
            "claim": claim,
            "domain": domain,
            "verdict": verdict,
            "confidence": confidence,
            "created_at": datetime.utcnow().isoformat(),
            "challenge_deadline": (datetime.utcnow() + timedelta(hours=self.config.challenge_window)).isoformat()
        }
        logger.info(f"Registered verdict {verdict_id} for potential challenges")
        return verdict_data
    
    # ==================== CHALLENGE OPERATIONS ====================
    
    def submit_challenge(
        self,
        verdict_id: str,
        challenger_wallet: str,
        stake_amount: float,
        evidence_links: List[str],
        explanation: str,
        original_claim: str = None,
        original_verdict: str = None,
        original_confidence: float = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Submit a new challenge to a verdict.
        
        Returns: (success, message, challenge_data)
        """
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
        
        # Check for existing active challenge on this verdict
        existing = db.get_challenges_by_verdict(verdict_id)
        active = [c for c in existing if c["status"] in ("pending", "voting")]
        if active:
            return False, "This verdict already has an active challenge", None
        
        # Check user's active challenges
        all_active = db.get_active_challenges()
        user_active = [c for c in all_active if c["challenger_wallet"] == challenger_wallet]
        if len(user_active) >= self.config.max_active_challenges_per_user:
            return False, f"Maximum {self.config.max_active_challenges_per_user} active challenges allowed", None
        
        # Reserve treasury funds
        treasury = db.get_treasury()
        required_reserve = stake_amount * (self.config.winner_multiplier - 1)
        available = treasury["total_balance"] - treasury["reserved_for_payouts"]
        
        if available < required_reserve:
            return False, "Insufficient treasury funds to back this challenge", None
        
        # Update treasury reservation
        db.update_treasury({
            "reserved_for_payouts": treasury["reserved_for_payouts"] + required_reserve,
            "total_staked_all_time": treasury["total_staked_all_time"] + stake_amount,
            "total_challenges": treasury["total_challenges"] + 1
        })
        
        # Create challenge
        challenge_id = generate_id("ch_")
        voting_deadline = (datetime.utcnow() + timedelta(hours=self.config.voting_period)).isoformat()
        
        challenge_data = {
            "challenge_id": challenge_id,
            "verdict_id": verdict_id,
            "original_claim": original_claim,
            "original_verdict": original_verdict,
            "original_confidence": original_confidence,
            "challenger_wallet": challenger_wallet,
            "stake_amount": stake_amount,
            "evidence_links": evidence_links,
            "explanation": explanation,
            "status": "voting",
            "voting_deadline": voting_deadline,
            "created_at": datetime.utcnow().isoformat()
        }
        
        db.create_challenge(challenge_data)
        
        # Record transaction
        db.add_treasury_transaction({
            "tx_id": generate_id("tx_"),
            "tx_type": "stake_received",
            "amount": stake_amount,
            "challenge_id": challenge_id,
            "wallet": challenger_wallet,
            "description": f"Stake for challenge {challenge_id}"
        })
        
        # Update challenger reputation
        self._ensure_reputation(challenger_wallet)
        rep = db.get_voter_reputation(challenger_wallet)
        db.create_or_update_reputation(challenger_wallet, {
            "total_challenges": rep["total_challenges"] + 1
        })
        
        logger.info(f"Challenge {challenge_id} submitted by {challenger_wallet} with {stake_amount} SOL")
        
        return True, "Challenge submitted successfully", challenge_data
    
    def get_challenge(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        """Get challenge by ID."""
        return db.get_challenge(challenge_id)
    
    def get_active_challenges(self) -> List[Dict[str, Any]]:
        """Get all active challenges."""
        return db.get_active_challenges()
    
    def get_challenges_by_verdict(self, verdict_id: str) -> List[Dict[str, Any]]:
        """Get all challenges for a verdict."""
        return db.get_challenges_by_verdict(verdict_id)
    
    # ==================== VOTING OPERATIONS ====================
    
    def cast_vote(
        self,
        challenge_id: str,
        voter_wallet: str,
        position: str,  # "ai" or "challenger"
        reasoning: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Cast a vote on a challenge.
        
        Returns: (success, message, vote_data)
        """
        challenge = db.get_challenge(challenge_id)
        if not challenge:
            return False, "Challenge not found", None
        
        if challenge["status"] != "voting":
            return False, "Voting is not open for this challenge", None
        
        # Check voting deadline
        deadline = datetime.fromisoformat(challenge["voting_deadline"])
        if datetime.utcnow() > deadline:
            return False, "Voting period has ended", None
        
        # Check if already voted
        if db.has_voted(challenge_id, voter_wallet):
            return False, "You have already voted on this challenge", None
        
        # Cannot vote on own challenge
        if challenge["challenger_wallet"] == voter_wallet:
            return False, "Cannot vote on your own challenge", None
        
        # Get voter info for weight calculation
        self._ensure_reputation(voter_wallet)
        voter = db.get_voter_reputation(voter_wallet)
        
        # Calculate vote weight
        weight = self._calculate_vote_weight(voter)
        
        # Create vote
        vote_id = generate_id("vote_")
        vote_data = {
            "vote_id": vote_id,
            "challenge_id": challenge_id,
            "voter_wallet": voter_wallet,
            "position": position,
            "weight": weight,
            "reasoning": reasoning,
            "created_at": datetime.utcnow().isoformat()
        }
        
        db.create_vote(vote_data)
        
        # Update challenge vote counts
        if position == "ai":
            new_ai_votes = challenge["votes_for_ai"] + weight
            db.update_challenge(challenge_id, {"votes_for_ai": new_ai_votes})
        else:
            new_challenger_votes = challenge["votes_for_challenger"] + weight
            db.update_challenge(challenge_id, {"votes_for_challenger": new_challenger_votes})
        
        # Update voter stats
        db.create_or_update_reputation(voter_wallet, {
            "total_votes": voter["total_votes"] + 1
        })
        
        logger.info(f"Vote {vote_id} cast by {voter_wallet} for {position} with weight {weight:.2f}")
        
        # Check if we should auto-resolve
        updated_challenge = db.get_challenge(challenge_id)
        self._check_auto_resolve(updated_challenge)
        
        return True, "Vote cast successfully", vote_data
    
    def get_votes(self, challenge_id: str) -> List[Dict[str, Any]]:
        """Get all votes for a challenge."""
        return db.get_votes_for_challenge(challenge_id)
    
    def _calculate_vote_weight(self, voter: Dict[str, Any]) -> float:
        """Calculate vote weight based on voter reputation."""
        base_weight = 1.0
        
        # Reputation bonus (sqrt scaling to prevent domination)
        rep_bonus = min(voter.get("reputation", 100) / 100, 2.0)
        
        # Accuracy bonus
        accuracy = voter.get("accuracy_rate", 0.5)
        accuracy_bonus = accuracy * 0.5  # Up to 0.5 bonus
        
        return base_weight + rep_bonus + accuracy_bonus
    
    # ==================== RESOLUTION ====================
    
    def _check_auto_resolve(self, challenge: Dict[str, Any]):
        """Check if challenge should be auto-resolved."""
        total_votes = challenge["votes_for_ai"] + challenge["votes_for_challenger"]
        
        # Check if past deadline
        deadline = datetime.fromisoformat(challenge["voting_deadline"])
        past_deadline = datetime.utcnow() > deadline
        
        # Check if minimum votes reached
        min_votes = self.config.min_votes_for_resolution
        enough_votes = total_votes >= min_votes
        
        if past_deadline and enough_votes:
            self.resolve_challenge(challenge["challenge_id"])
    
    def resolve_challenge(self, challenge_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Resolve a challenge and process payouts.
        
        Returns: (success, message, result)
        """
        challenge = db.get_challenge(challenge_id)
        if not challenge:
            return False, "Challenge not found", None
        
        if challenge["status"] != "voting":
            return False, "Challenge is not in voting status", None
        
        total_votes = challenge["votes_for_ai"] + challenge["votes_for_challenger"]
        
        if total_votes < self.config.min_votes_for_resolution:
            return False, f"Minimum {self.config.min_votes_for_resolution} votes required", None
        
        # Determine winner
        ai_wins = challenge["votes_for_ai"] > challenge["votes_for_challenger"]
        
        if ai_wins:
            result = self._process_ai_win(challenge)
        else:
            result = self._process_challenger_win(challenge)
        
        return True, "Challenge resolved", result
    
    def _process_ai_win(self, challenge: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI winning the challenge."""
        stake = challenge["stake_amount"]
        
        # Update challenge status
        db.update_challenge(challenge["challenge_id"], {
            "status": "resolved_ai_win",
            "resolution_reason": f"AI won with {challenge['votes_for_ai']:.1f} vs {challenge['votes_for_challenger']:.1f} votes",
            "resolved_at": datetime.utcnow().isoformat()
        })
        
        # Release reservation and add stake to treasury
        treasury = db.get_treasury()
        reserved_amount = stake * (self.config.winner_multiplier - 1)
        
        db.update_treasury({
            "total_balance": treasury["total_balance"] + stake,
            "reserved_for_payouts": treasury["reserved_for_payouts"] - reserved_amount,
            "ai_wins": treasury["ai_wins"] + 1
        })
        
        # Record transaction
        db.add_treasury_transaction({
            "tx_id": generate_id("tx_"),
            "tx_type": "ai_win_deposit",
            "amount": stake,
            "challenge_id": challenge["challenge_id"],
            "wallet": challenge["challenger_wallet"],
            "description": f"Forfeited stake from challenge {challenge['challenge_id']}"
        })
        
        # Update voter accuracies
        self._update_voter_accuracies(challenge["challenge_id"], "ai")
        
        logger.info(f"Challenge {challenge['challenge_id']} resolved: AI wins, {stake} SOL added to treasury")
        
        return {
            "winner": "ai",
            "stake_amount": stake,
            "treasury_received": stake,
            "votes_for_ai": challenge["votes_for_ai"],
            "votes_for_challenger": challenge["votes_for_challenger"]
        }
    
    def _process_challenger_win(self, challenge: Dict[str, Any]) -> Dict[str, Any]:
        """Process challenger winning."""
        stake = challenge["stake_amount"]
        payout = stake * self.config.winner_multiplier
        
        # Update challenge status
        db.update_challenge(challenge["challenge_id"], {
            "status": "resolved_user_win",
            "resolution_reason": f"Challenger won with {challenge['votes_for_challenger']:.1f} vs {challenge['votes_for_ai']:.1f} votes",
            "payout_amount": payout,
            "resolved_at": datetime.utcnow().isoformat()
        })
        
        # Process payout from treasury
        treasury = db.get_treasury()
        reserved_amount = stake * (self.config.winner_multiplier - 1)
        
        db.update_treasury({
            "total_balance": treasury["total_balance"] - reserved_amount,
            "reserved_for_payouts": treasury["reserved_for_payouts"] - reserved_amount,
            "total_paid_out": treasury["total_paid_out"] + payout,
            "challenger_wins": treasury["challenger_wins"] + 1
        })
        
        # Record transaction
        db.add_treasury_transaction({
            "tx_id": generate_id("tx_"),
            "tx_type": "payout",
            "amount": payout,
            "challenge_id": challenge["challenge_id"],
            "wallet": challenge["challenger_wallet"],
            "description": f"Payout for winning challenge {challenge['challenge_id']}"
        })
        
        # Update challenger reputation
        rep = db.get_voter_reputation(challenge["challenger_wallet"])
        if rep:
            db.create_or_update_reputation(challenge["challenger_wallet"], {
                "successful_challenges": rep["successful_challenges"] + 1,
                "total_won": rep["total_won"] + payout,
                "reputation": rep["reputation"] + 50  # Big reputation boost
            })
        
        # Update voter accuracies
        self._update_voter_accuracies(challenge["challenge_id"], "challenger")
        
        logger.info(f"Challenge {challenge['challenge_id']} resolved: Challenger wins, {payout} SOL payout")
        
        return {
            "winner": "challenger",
            "stake_amount": stake,
            "payout_amount": payout,
            "votes_for_ai": challenge["votes_for_ai"],
            "votes_for_challenger": challenge["votes_for_challenger"]
        }
    
    def _update_voter_accuracies(self, challenge_id: str, winner: str):
        """Update accuracy for all voters on a resolved challenge."""
        votes = db.get_votes_for_challenge(challenge_id)
        
        for vote in votes:
            voter = db.get_voter_reputation(vote["voter_wallet"])
            if not voter:
                continue
            
            was_correct = vote["position"] == winner
            new_correct = voter["correct_votes"] + (1 if was_correct else 0)
            new_total = voter["total_votes"]
            new_accuracy = new_correct / new_total if new_total > 0 else 0.5
            
            # Reputation change
            rep_delta = 10 if was_correct else -5
            
            db.create_or_update_reputation(vote["voter_wallet"], {
                "correct_votes": new_correct,
                "accuracy_rate": new_accuracy,
                "reputation": max(0, voter["reputation"] + rep_delta)
            })
    
    def _ensure_reputation(self, wallet: str):
        """Ensure a wallet has a reputation record."""
        if not db.get_voter_reputation(wallet):
            db.create_or_update_reputation(wallet, {
                "reputation": 100,
                "total_votes": 0,
                "correct_votes": 0,
                "accuracy_rate": 0.5,
                "total_challenges": 0,
                "successful_challenges": 0,
                "total_won": 0.0
            })
    
    # ==================== TREASURY ====================
    
    def get_treasury_stats(self) -> Dict[str, Any]:
        """Get treasury statistics."""
        treasury = db.get_treasury()
        treasury["available_balance"] = treasury["total_balance"] - treasury["reserved_for_payouts"]
        return treasury
    
    def get_treasury_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent treasury transactions."""
        return db.get_treasury_transactions(limit)
    
    # ==================== LEADERBOARDS ====================
    
    def get_top_challengers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top challengers by winnings."""
        challengers = db.get_top_challengers(limit)
        return [{
            "wallet": c["wallet"],
            "challenges": c["total_challenges"],
            "wins": c["successful_challenges"],
            "total_won": c["total_won"]
        } for c in challengers]
    
    def get_top_voters(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top voters by accuracy."""
        voters = db.get_top_voters(limit)
        return [{
            "wallet": v["wallet"],
            "votes": v["total_votes"],
            "accuracy": v["accuracy_rate"],
            "reputation": v["reputation"]
        } for v in voters]
    
    def get_voter_stats(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get stats for a specific voter."""
        return db.get_voter_reputation(wallet)
    
    # ==================== VERIFICATION HISTORY ====================
    
    def save_verification(self, wallet: Optional[str], data: Dict[str, Any]) -> int:
        """Save a verification to history."""
        return db.save_verification(wallet, data)
    
    def get_user_history(self, wallet: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get verification history for a wallet."""
        return db.get_user_history(wallet, limit)
    
    # ==================== MAINTENANCE ====================
    
    def resolve_expired_challenges(self) -> List[str]:
        """Resolve all challenges past their deadline with enough votes."""
        resolved = []
        active = db.get_active_challenges()
        
        for challenge in active:
            deadline = datetime.fromisoformat(challenge["voting_deadline"])
            if datetime.utcnow() > deadline:
                total_votes = challenge["votes_for_ai"] + challenge["votes_for_challenger"]
                if total_votes >= self.config.min_votes_for_resolution:
                    success, _, _ = self.resolve_challenge(challenge["challenge_id"])
                    if success:
                        resolved.append(challenge["challenge_id"])
        
        return resolved
    
    def check_and_resolve_challenges(self) -> List[Tuple[str, str]]:
        """
        Check and resolve all challenges whose voting period has ended.
        Alias for resolve_expired_challenges that returns (challenge_id, outcome) tuples.
        """
        results = []
        active = db.get_active_challenges()
        
        for challenge in active:
            deadline = datetime.fromisoformat(challenge["voting_deadline"])
            if datetime.utcnow() > deadline:
                total_votes = challenge["votes_for_ai"] + challenge["votes_for_challenger"]
                if total_votes >= self.config.min_votes_for_resolution:
                    success, message, result = self.resolve_challenge(challenge["challenge_id"])
                    if success and result:
                        outcome = "ai_win" if result.get("winner") == "ai" else "challenger_win"
                        results.append((challenge["challenge_id"], outcome))
        
        return results
    
    def archive_old_challenges(self, cutoff: datetime) -> int:
        """Archive challenges older than the cutoff date."""
        # For SQLite, we'll just return 0 - archiving handled by database
        # In production, this could move old data to cold storage
        return 0
    
    def get_challenges_by_wallet(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get all challenges submitted by a wallet."""
        return db.get_challenges_by_wallet(wallet_address)
    
    def get_votes_for_challenge(self, challenge_id: str) -> List[Dict[str, Any]]:
        """Get all votes for a challenge."""
        return db.get_votes_for_challenge(challenge_id)
    
    def get_or_create_voter(self, wallet_address: str) -> Dict[str, Any]:
        """Get or create a voter record."""
        self._ensure_reputation(wallet_address)
        return db.get_voter_reputation(wallet_address) or {
            "wallet": wallet_address,
            "reputation": 1.0,
            "total_votes": 0,
            "accuracy_rate": 0.0
        }
    
    def is_verdict_challengeable(self, verdict_id: str) -> Tuple[bool, str]:
        """Check if a verdict can be challenged."""
        verdict = db.get_verdict(verdict_id)
        if not verdict:
            return False, "Verdict not found"
        
        # Check if already challenged
        existing = db.get_challenges_by_verdict(verdict_id)
        active = [c for c in existing if c.get("status") in ["pending", "voting"]]
        if active:
            return False, "Verdict already has an active challenge"
        
        # Check time window
        created_at = datetime.fromisoformat(verdict["created_at"])
        window_end = created_at + timedelta(hours=self.config.challenge_window)
        if datetime.utcnow() > window_end:
            return False, "Challenge window has expired"
        
        return True, "Verdict can be challenged"
    
    def get_verdict(self, verdict_id: str) -> Optional[Dict[str, Any]]:
        """Get a registered verdict."""
        return db.get_verdict(verdict_id)
    
    def force_resolve(self, challenge_id: str, winner: str, reason: str) -> Tuple[bool, str]:
        """Admin force-resolve a challenge."""
        challenge = db.get_challenge(challenge_id)
        if not challenge:
            return False, "Challenge not found"
        
        if challenge["status"] not in ["pending", "voting"]:
            return False, f"Challenge cannot be resolved (status: {challenge['status']})"
        
        # Update challenge
        challenge["status"] = f"resolved_{winner}_win"
        challenge["resolved_at"] = datetime.utcnow().isoformat()
        challenge["resolution_reason"] = reason
        db.update_challenge(challenge_id, challenge)
        
        # Process payout
        if winner == "ai":
            self._process_ai_win(challenge)
        else:
            self._process_challenger_win(challenge)
        
        return True, f"Challenge force-resolved: {winner} wins"
    
    def add_treasury_funds(self, amount: float) -> None:
        """Add funds to the treasury."""
        db.add_treasury_transaction({
            "type": "deposit",
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat(),
            "description": "Manual treasury deposit"
        })
    
    def get_challenger_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top challengers."""
        return self.get_top_challengers(limit)
    
    def get_voter_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top voters."""
        return self.get_top_voters(limit)


# Singleton instance
_dow_manager_v2: Optional[DOWManagerV2] = None


def get_dow_manager() -> DOWManagerV2:
    """Get the singleton DOW manager instance."""
    global _dow_manager_v2
    if _dow_manager_v2 is None:
        _dow_manager_v2 = DOWManagerV2()
    return _dow_manager_v2
