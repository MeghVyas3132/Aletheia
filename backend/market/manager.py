"""
Truth Market Manager - Aletheia V2

Core market operations:
- Create markets from verified claims
- Place and manage bets
- Calculate odds dynamically
- Resolve markets and distribute payouts
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from market.models import (
    Market, Bet, User, 
    MarketStatus, BetPosition, ResolutionOutcome,
    LeaderboardEntry, Fees,
    generate_market_id, generate_bet_id, generate_user_id, hash_claim
)


class TruthMarketManager:
    """
    Manages the Truth Market prediction system.
    
    This is a mocked implementation - data is stored in memory.
    In production, this would use a database.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "market_data.json"
        
        # In-memory storage (mocked database)
        self.users: Dict[str, User] = {}
        self.markets: Dict[str, Market] = {}
        self.bets: Dict[str, Bet] = {}
        
        # Initial tokens for new users
        self.INITIAL_BALANCE = 1000.0
        
        # Load existing data if available
        self._load_data()
    
    def _load_data(self):
        """Load data from storage file."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    # Reconstruct objects from dicts
                    # (simplified - in production use proper serialization)
        except Exception as e:
            print(f"Could not load market data: {e}")
    
    def _save_data(self):
        """Save data to storage file."""
        try:
            data = {
                "users": {k: v.to_dict() for k, v in self.users.items()},
                "markets": {k: v.to_dict() for k, v in self.markets.items()},
                "bets": {k: v.to_dict() for k, v in self.bets.items()}
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Could not save market data: {e}")
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, username: str) -> User:
        """Create a new user with initial token balance."""
        user_id = generate_user_id()
        user = User(
            user_id=user_id,
            username=username,
            balance=self.INITIAL_BALANCE
        )
        self.users[user_id] = user
        self._save_data()
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_or_create_user(self, username: str) -> User:
        """Get existing user by username or create new one."""
        for user in self.users.values():
            if user.username == username:
                return user
        return self.create_user(username)
    
    def get_user_balance(self, user_id: str) -> float:
        """Get user's token balance."""
        user = self.users.get(user_id)
        return user.balance if user else 0.0
    
    def add_tokens(self, user_id: str, amount: float) -> bool:
        """Add tokens to user's balance (for testing/rewards)."""
        user = self.users.get(user_id)
        if user:
            user.balance += amount
            self._save_data()
            return True
        return False
    
    # ==================== MARKET MANAGEMENT ====================
    
    def create_market(
        self,
        claim: str,
        aletheia_verdict: str,
        aletheia_confidence: float,
        verdict_summary: str,
        category: str = "general",
        duration_days: int = 7
    ) -> Market:
        """
        Create a new prediction market from an Aletheia verdict.
        """
        market_id = generate_market_id()
        claim_hash = hash_claim(claim)
        
        # Check for duplicate markets
        for existing in self.markets.values():
            if existing.claim_hash == claim_hash and existing.status == MarketStatus.OPEN:
                return existing  # Return existing market instead
        
        closes_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        market = Market(
            market_id=market_id,
            claim=claim,
            claim_hash=claim_hash,
            aletheia_verdict=aletheia_verdict,
            aletheia_confidence=aletheia_confidence,
            verdict_summary=verdict_summary,
            category=category,
            status=MarketStatus.OPEN,
            closes_at=closes_at
        )
        
        self.markets[market_id] = market
        self._save_data()
        return market
    
    def get_market(self, market_id: str) -> Optional[Market]:
        """Get market by ID."""
        return self.markets.get(market_id)
    
    def get_open_markets(self) -> List[Market]:
        """Get all open markets."""
        open_markets = []
        for market in self.markets.values():
            if market.is_open():
                open_markets.append(market)
        return sorted(open_markets, key=lambda m: m.total_pool, reverse=True)
    
    def get_markets_by_category(self, category: str) -> List[Market]:
        """Get markets filtered by category."""
        return [m for m in self.get_open_markets() if m.category == category]
    
    def get_hot_markets(self, limit: int = 10) -> List[Market]:
        """Get markets with most volume."""
        return self.get_open_markets()[:limit]
    
    def get_ending_soon(self, limit: int = 10) -> List[Market]:
        """Get markets ending soon."""
        open_markets = self.get_open_markets()
        return sorted(
            open_markets,
            key=lambda m: datetime.fromisoformat(m.closes_at)
        )[:limit]
    
    # ==================== BETTING ====================
    
    def place_bet(
        self,
        user_id: str,
        market_id: str,
        position: BetPosition,
        amount: float
    ) -> Tuple[Optional[Bet], str]:
        """
        Place a bet on a market.
        
        Returns:
            Tuple of (Bet if successful, error message if failed)
        """
        # Validate user
        user = self.users.get(user_id)
        if not user:
            return None, "User not found"
        
        # Validate market
        market = self.markets.get(market_id)
        if not market:
            return None, "Market not found"
        
        if not market.is_open():
            return None, "Market is closed"
        
        # Calculate total cost (amount + gas fee)
        total_cost = amount + Fees.GAS_FEE
        
        # Check balance
        if user.balance < total_cost:
            return None, f"Insufficient balance. Need {total_cost:.2f} ALETH, have {user.balance:.2f}"
        
        # Calculate odds at time of bet
        if position == BetPosition.CORRECT:
            odds = market.correct_odds
            payout_multiplier = market.correct_payout_multiplier
        else:
            odds = market.wrong_odds
            payout_multiplier = market.wrong_payout_multiplier
        
        # Calculate potential payout (minus platform fee)
        gross_payout = amount * payout_multiplier
        platform_fee = gross_payout * Fees.PLATFORM_FEE_PERCENT
        potential_payout = gross_payout - platform_fee
        
        # Create bet
        bet_id = generate_bet_id()
        bet = Bet(
            bet_id=bet_id,
            user_id=user_id,
            market_id=market_id,
            position=position,
            amount=amount,
            odds_at_bet=odds,
            potential_payout=potential_payout
        )
        
        # Deduct from user balance
        user.balance -= total_cost
        user.total_bets += 1
        
        # Add to market pool
        if position == BetPosition.CORRECT:
            market.correct_pool += amount
        else:
            market.wrong_pool += amount
        
        market.total_bettors += 1
        market.bets.append(bet_id)
        
        # Store bet
        self.bets[bet_id] = bet
        self._save_data()
        
        return bet, "Bet placed successfully"
    
    def get_user_bets(self, user_id: str) -> List[Bet]:
        """Get all bets by a user."""
        return [b for b in self.bets.values() if b.user_id == user_id]
    
    def get_user_active_bets(self, user_id: str) -> List[Bet]:
        """Get active (unresolved) bets by a user."""
        return [b for b in self.get_user_bets(user_id) if b.status == "active"]
    
    def get_market_bets(self, market_id: str) -> List[Bet]:
        """Get all bets on a market."""
        return [b for b in self.bets.values() if b.market_id == market_id]
    
    # ==================== RESOLUTION ====================
    
    def resolve_market(
        self,
        market_id: str,
        outcome: ResolutionOutcome,
        resolution_source: str = "",
        resolution_evidence: str = ""
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Resolve a market and calculate payouts.
        
        Returns:
            Tuple of (success, message, list of payout details)
        """
        market = self.markets.get(market_id)
        if not market:
            return False, "Market not found", []
        
        if market.status == MarketStatus.RESOLVED:
            return False, "Market already resolved", []
        
        # Close market
        market.status = MarketStatus.RESOLVED
        market.resolution = outcome
        market.resolution_source = resolution_source
        market.resolution_evidence = resolution_evidence
        market.resolved_at = datetime.now().isoformat()
        
        # Calculate payouts
        payouts = []
        market_bets = self.get_market_bets(market_id)
        
        # Determine winning position
        if outcome == ResolutionOutcome.ALETHEIA_CORRECT:
            winning_position = BetPosition.CORRECT
            winning_pool = market.correct_pool
            losing_pool = market.wrong_pool
        elif outcome == ResolutionOutcome.ALETHEIA_WRONG:
            winning_position = BetPosition.WRONG
            winning_pool = market.wrong_pool
            losing_pool = market.correct_pool
        else:  # VOIDED
            # Refund all bets
            for bet in market_bets:
                user = self.users.get(bet.user_id)
                if user:
                    user.balance += bet.amount  # Refund original amount
                    bet.status = "refunded"
                    bet.payout = bet.amount
                    payouts.append({
                        "bet_id": bet.bet_id,
                        "user_id": bet.user_id,
                        "refund": bet.amount
                    })
            self._save_data()
            return True, "Market voided, all bets refunded", payouts
        
        # Calculate payouts for each bet
        total_pool = market.total_pool
        
        for bet in market_bets:
            user = self.users.get(bet.user_id)
            if not user:
                continue
            
            if bet.position == winning_position:
                # Winner!
                # Payout = (bet_amount / winning_pool) * total_pool
                if winning_pool > 0:
                    share = bet.amount / winning_pool
                    gross_payout = share * total_pool
                    platform_fee = gross_payout * Fees.PLATFORM_FEE_PERCENT
                    net_payout = gross_payout - platform_fee
                else:
                    net_payout = bet.amount  # Edge case: refund
                
                user.balance += net_payout
                user.wins += 1
                user.total_profit += (net_payout - bet.amount)
                bet.status = "won"
                bet.payout = net_payout
                
                payouts.append({
                    "bet_id": bet.bet_id,
                    "user_id": bet.user_id,
                    "position": bet.position.value,
                    "bet_amount": bet.amount,
                    "payout": net_payout,
                    "profit": net_payout - bet.amount,
                    "result": "won"
                })
            else:
                # Loser
                user.losses += 1
                user.total_profit -= bet.amount
                bet.status = "lost"
                bet.payout = 0
                
                payouts.append({
                    "bet_id": bet.bet_id,
                    "user_id": bet.user_id,
                    "position": bet.position.value,
                    "bet_amount": bet.amount,
                    "payout": 0,
                    "profit": -bet.amount,
                    "result": "lost"
                })
        
        self._save_data()
        return True, f"Market resolved: {outcome.value}", payouts
    
    # ==================== LEADERBOARD ====================
    
    def get_leaderboard(self, limit: int = 10) -> List[LeaderboardEntry]:
        """Get top users by profit."""
        # Sort users by total profit
        sorted_users = sorted(
            self.users.values(),
            key=lambda u: u.total_profit,
            reverse=True
        )
        
        leaderboard = []
        for i, user in enumerate(sorted_users[:limit]):
            leaderboard.append(LeaderboardEntry(
                rank=i + 1,
                user_id=user.user_id,
                username=user.username,
                win_rate=user.win_rate,
                total_profit=user.total_profit,
                total_bets=user.total_bets,
                current_streak=0  # TODO: Implement streak tracking
            ))
        
        return leaderboard
    
    # ==================== STATS ====================
    
    def get_platform_stats(self) -> Dict:
        """Get overall platform statistics."""
        total_volume = sum(m.total_pool for m in self.markets.values())
        open_markets = len([m for m in self.markets.values() if m.is_open()])
        resolved_markets = len([m for m in self.markets.values() if m.status == MarketStatus.RESOLVED])
        total_users = len(self.users)
        total_bets = len(self.bets)
        
        return {
            "total_volume": total_volume,
            "open_markets": open_markets,
            "resolved_markets": resolved_markets,
            "total_users": total_users,
            "total_bets": total_bets
        }
    
    def get_user_stats(self, user_id: str) -> Optional[Dict]:
        """Get stats for a specific user."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        active_bets = self.get_user_active_bets(user_id)
        total_at_risk = sum(b.amount for b in active_bets)
        
        return {
            "user": user.to_dict(),
            "active_bets_count": len(active_bets),
            "total_at_risk": total_at_risk,
            "potential_winnings": sum(b.potential_payout for b in active_bets)
        }


# Singleton instance
_market_manager: Optional[TruthMarketManager] = None


def get_market_manager() -> TruthMarketManager:
    """Get the singleton market manager instance."""
    global _market_manager
    if _market_manager is None:
        _market_manager = TruthMarketManager()
    return _market_manager
