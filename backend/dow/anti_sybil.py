"""
Anti-Sybil Protection - Aletheia DOW

Prevents vote manipulation through:
1. Wallet age verification (via Solana RPC)
2. Minimum SOL balance requirements
3. Transaction history analysis
4. Rate limiting per wallet
5. Reputation-based trust scoring
"""

import os
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class AntiSybilConfig:
    """Configuration for anti-sybil protection."""
    # Wallet requirements
    min_wallet_age_days: int = 7  # Minimum age of wallet to vote
    min_sol_balance: float = 0.01  # Minimum SOL balance to vote
    min_transaction_count: int = 5  # Minimum transactions to vote
    
    # Rate limiting
    max_votes_per_hour: int = 10
    max_challenges_per_day: int = 3
    
    # Trust scoring
    new_wallet_trust: float = 0.3  # Trust score for new wallets
    max_trust_score: float = 1.0
    
    # Verification modes
    strict_mode: bool = False  # If True, requires on-chain verification
    demo_mode: bool = True  # If True, skips actual blockchain checks


class AntiSybilProtection:
    """
    Anti-sybil protection for the DOW voting system.
    
    In production, this would connect to Solana RPC to verify:
    - Wallet creation date (first transaction)
    - Current SOL balance
    - Transaction history
    """
    
    def __init__(self, config: AntiSybilConfig = None):
        self.config = config or AntiSybilConfig()
        
        # Rate limiting state (in-memory, would use Redis in production)
        self._vote_timestamps: Dict[str, list] = {}
        self._challenge_timestamps: Dict[str, list] = {}
        
        # Cached wallet info
        self._wallet_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour cache
        
        logger.info(f"AntiSybilProtection initialized (demo_mode={self.config.demo_mode})")
    
    async def verify_wallet_for_voting(self, wallet_address: str) -> Tuple[bool, str, float]:
        """
        Verify if a wallet is eligible to vote.
        
        Returns: (is_eligible, reason, trust_score)
        """
        # Check rate limiting first
        if self._is_vote_rate_limited(wallet_address):
            return False, "Rate limited: Too many votes. Please wait.", 0.0
        
        # Get wallet info
        wallet_info = await self._get_wallet_info(wallet_address)
        
        # Check wallet age
        if wallet_info["age_days"] < self.config.min_wallet_age_days:
            return False, f"Wallet must be at least {self.config.min_wallet_age_days} days old", 0.0
        
        # Check balance
        if wallet_info["balance"] < self.config.min_sol_balance:
            return False, f"Minimum {self.config.min_sol_balance} SOL balance required", 0.0
        
        # Check transaction count
        if wallet_info["tx_count"] < self.config.min_transaction_count:
            return False, f"Wallet needs at least {self.config.min_transaction_count} transactions", 0.0
        
        # Calculate trust score
        trust_score = self._calculate_trust_score(wallet_info)
        
        # Record vote timestamp
        self._record_vote(wallet_address)
        
        return True, "OK", trust_score
    
    async def verify_wallet_for_challenge(self, wallet_address: str, stake_amount: float) -> Tuple[bool, str]:
        """
        Verify if a wallet is eligible to submit a challenge.
        
        Returns: (is_eligible, reason)
        """
        # Check rate limiting
        if self._is_challenge_rate_limited(wallet_address):
            return False, f"Rate limited: Maximum {self.config.max_challenges_per_day} challenges per day"
        
        # Get wallet info
        wallet_info = await self._get_wallet_info(wallet_address)
        
        # Stricter requirements for challenges
        min_age = self.config.min_wallet_age_days * 2  # Double the age requirement
        if wallet_info["age_days"] < min_age:
            return False, f"Wallet must be at least {min_age} days old to challenge"
        
        # Check balance (must have enough for stake + buffer)
        required_balance = stake_amount + 0.1  # Buffer for transaction fees
        if wallet_info["balance"] < required_balance:
            return False, f"Insufficient balance. Need {required_balance} SOL"
        
        # Record challenge timestamp
        self._record_challenge(wallet_address)
        
        return True, "OK"
    
    async def _get_wallet_info(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get wallet information (with caching).
        
        In production, this would query Solana RPC.
        """
        # Check cache
        if wallet_address in self._wallet_cache:
            cached = self._wallet_cache[wallet_address]
            if time.time() - cached["_cached_at"] < self._cache_ttl:
                return cached
        
        # Fetch wallet info
        if self.config.demo_mode:
            # Demo mode: Return fake data that passes verification
            wallet_info = self._get_demo_wallet_info(wallet_address)
        else:
            # Production mode: Query Solana RPC
            wallet_info = await self._fetch_solana_wallet_info(wallet_address)
        
        # Cache it
        wallet_info["_cached_at"] = time.time()
        self._wallet_cache[wallet_address] = wallet_info
        
        return wallet_info
    
    def _get_demo_wallet_info(self, wallet_address: str) -> Dict[str, Any]:
        """
        Generate demo wallet info that passes basic verification.
        """
        # Use wallet address hash to generate consistent fake data
        addr_hash = hash(wallet_address)
        
        return {
            "address": wallet_address,
            "age_days": 30 + (addr_hash % 365),  # 30-395 days old
            "balance": 1.0 + (addr_hash % 100) / 10,  # 1-11 SOL
            "tx_count": 10 + (addr_hash % 100),  # 10-110 transactions
            "first_tx_date": (datetime.now() - timedelta(days=30 + (addr_hash % 365))).isoformat(),
            "is_program": False,
            "is_verified": True,
        }
    
    async def _fetch_solana_wallet_info(self, wallet_address: str) -> Dict[str, Any]:
        """
        Fetch real wallet info from Solana RPC.
        
        Requires: SOLANA_RPC_URL environment variable
        """
        import httpx
        
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
        
        async with httpx.AsyncClient() as client:
            # Get balance
            balance_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            })
            balance_data = balance_resp.json()
            balance_lamports = balance_data.get("result", {}).get("value", 0)
            balance_sol = balance_lamports / 1_000_000_000
            
            # Get transaction signatures to estimate age and activity
            sigs_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet_address, {"limit": 100}]
            })
            sigs_data = sigs_resp.json()
            signatures = sigs_data.get("result", [])
            
            tx_count = len(signatures)
            
            # Estimate age from oldest transaction
            if signatures:
                oldest_sig = signatures[-1]
                oldest_time = oldest_sig.get("blockTime", time.time())
                age_days = (time.time() - oldest_time) / 86400
            else:
                age_days = 0
            
            return {
                "address": wallet_address,
                "age_days": int(age_days),
                "balance": balance_sol,
                "tx_count": tx_count,
                "first_tx_date": datetime.fromtimestamp(oldest_time).isoformat() if signatures else None,
                "is_program": False,
                "is_verified": True,
            }
    
    def _calculate_trust_score(self, wallet_info: Dict[str, Any]) -> float:
        """
        Calculate a trust score for a wallet (0.0 to 1.0).
        
        Higher scores give more vote weight.
        """
        score = self.config.new_wallet_trust
        
        # Age bonus (up to +0.3 for 1 year old)
        age_bonus = min(wallet_info["age_days"] / 365, 1.0) * 0.3
        score += age_bonus
        
        # Balance bonus (up to +0.2 for 10+ SOL)
        balance_bonus = min(wallet_info["balance"] / 10, 1.0) * 0.2
        score += balance_bonus
        
        # Activity bonus (up to +0.2 for 100+ transactions)
        tx_bonus = min(wallet_info["tx_count"] / 100, 1.0) * 0.2
        score += tx_bonus
        
        return min(score, self.config.max_trust_score)
    
    def _is_vote_rate_limited(self, wallet_address: str) -> bool:
        """Check if wallet is rate-limited for voting."""
        now = time.time()
        hour_ago = now - 3600
        
        if wallet_address not in self._vote_timestamps:
            return False
        
        # Filter to last hour
        recent = [t for t in self._vote_timestamps[wallet_address] if t > hour_ago]
        self._vote_timestamps[wallet_address] = recent
        
        return len(recent) >= self.config.max_votes_per_hour
    
    def _is_challenge_rate_limited(self, wallet_address: str) -> bool:
        """Check if wallet is rate-limited for challenges."""
        now = time.time()
        day_ago = now - 86400
        
        if wallet_address not in self._challenge_timestamps:
            return False
        
        # Filter to last day
        recent = [t for t in self._challenge_timestamps[wallet_address] if t > day_ago]
        self._challenge_timestamps[wallet_address] = recent
        
        return len(recent) >= self.config.max_challenges_per_day
    
    def _record_vote(self, wallet_address: str):
        """Record a vote timestamp for rate limiting."""
        if wallet_address not in self._vote_timestamps:
            self._vote_timestamps[wallet_address] = []
        self._vote_timestamps[wallet_address].append(time.time())
    
    def _record_challenge(self, wallet_address: str):
        """Record a challenge timestamp for rate limiting."""
        if wallet_address not in self._challenge_timestamps:
            self._challenge_timestamps[wallet_address] = []
        self._challenge_timestamps[wallet_address].append(time.time())
    
    def get_wallet_stats(self, wallet_address: str) -> Dict[str, Any]:
        """Get rate limiting stats for a wallet."""
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        
        votes_last_hour = len([
            t for t in self._vote_timestamps.get(wallet_address, [])
            if t > hour_ago
        ])
        
        challenges_last_day = len([
            t for t in self._challenge_timestamps.get(wallet_address, [])
            if t > day_ago
        ])
        
        return {
            "votes_last_hour": votes_last_hour,
            "votes_remaining": max(0, self.config.max_votes_per_hour - votes_last_hour),
            "challenges_last_day": challenges_last_day,
            "challenges_remaining": max(0, self.config.max_challenges_per_day - challenges_last_day),
        }
    
    async def is_eligible_to_vote(
        self, 
        wallet_address: str, 
        challenge_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if a wallet is eligible to vote.
        
        This is the main entry point for anti-sybil checks during voting.
        
        Args:
            wallet_address: The wallet address to check
            challenge_id: Optional challenge ID (for context)
            
        Returns:
            Tuple of (is_eligible, reason)
        """
        is_valid, reason, trust_score = await self.verify_wallet_for_voting(wallet_address)
        
        if not is_valid:
            return False, reason
            
        # Additional rate limit check
        can_vote, rate_reason = self.check_rate_limit(wallet_address, "vote")
        if not can_vote:
            return False, rate_reason
            
        return True, f"Eligible with trust score {trust_score:.2f}"


# Singleton instance
_anti_sybil: Optional[AntiSybilProtection] = None


def get_anti_sybil() -> AntiSybilProtection:
    """Get the singleton anti-sybil protection instance."""
    global _anti_sybil
    if _anti_sybil is None:
        _anti_sybil = AntiSybilProtection()
    return _anti_sybil


# Alias for easier import
get_anti_sybil_checker = get_anti_sybil
