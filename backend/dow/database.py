"""
SQLite Database for DOW (Decentralized Oracle of Wisdom)
Provides persistent storage for challenges, votes, treasury, and reputation.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database file path - use environment variable or fallback to local storage
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "dow.db")
DB_PATH = os.environ.get("DOW_DB_PATH", DEFAULT_DB_PATH)


def get_db_path() -> str:
    """Get database path, ensuring directory exists."""
    db_path = DB_PATH
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            # Fallback to current directory if storage can't be created
            db_path = os.path.join(os.path.dirname(__file__), "dow.db")
    return db_path


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize the database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Challenges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                challenge_id TEXT PRIMARY KEY,
                verdict_id TEXT NOT NULL,
                original_claim TEXT,
                original_verdict TEXT,
                original_confidence REAL,
                challenger_wallet TEXT NOT NULL,
                stake_amount REAL NOT NULL,
                evidence_links TEXT NOT NULL,  -- JSON array
                explanation TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                votes_for_ai REAL DEFAULT 0,
                votes_for_challenger REAL DEFAULT 0,
                voting_deadline TEXT,
                resolution_reason TEXT,
                payout_amount REAL,
                payout_tx_hash TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Votes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                vote_id TEXT PRIMARY KEY,
                challenge_id TEXT NOT NULL,
                voter_wallet TEXT NOT NULL,
                position TEXT NOT NULL,  -- 'ai' or 'challenger'
                weight REAL NOT NULL DEFAULT 1.0,
                reasoning TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (challenge_id) REFERENCES challenges(challenge_id),
                UNIQUE(challenge_id, voter_wallet)
            )
        """)
        
        # Treasury table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS treasury (
                id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton
                total_balance REAL DEFAULT 1000.0,
                reserved_for_payouts REAL DEFAULT 0.0,
                total_challenges INTEGER DEFAULT 0,
                ai_wins INTEGER DEFAULT 0,
                challenger_wins INTEGER DEFAULT 0,
                total_staked_all_time REAL DEFAULT 0.0,
                total_paid_out REAL DEFAULT 0.0,
                updated_at TEXT
            )
        """)
        
        # Treasury transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS treasury_transactions (
                tx_id TEXT PRIMARY KEY,
                tx_type TEXT NOT NULL,  -- 'stake_received', 'payout', 'ai_win_deposit'
                amount REAL NOT NULL,
                challenge_id TEXT,
                wallet TEXT,
                description TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Voter reputation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voter_reputation (
                wallet TEXT PRIMARY KEY,
                reputation REAL DEFAULT 100.0,
                total_votes INTEGER DEFAULT 0,
                correct_votes INTEGER DEFAULT 0,
                accuracy_rate REAL DEFAULT 0.5,
                total_challenges INTEGER DEFAULT 0,
                successful_challenges INTEGER DEFAULT 0,
                total_won REAL DEFAULT 0.0,
                domain_expertise TEXT,  -- JSON object
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        # User sessions table (for wallet-based auth)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                wallet TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Verification history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet TEXT,
                claim TEXT NOT NULL,
                verdict TEXT NOT NULL,
                confidence REAL,
                truth_probability REAL,
                summary TEXT,
                sources TEXT,  -- JSON
                created_at TEXT NOT NULL
            )
        """)
        
        # Verdicts table (for challenge tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verdicts (
                verdict_id TEXT PRIMARY KEY,
                claim TEXT NOT NULL,
                domain TEXT,
                verdict TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Initialize treasury if empty
        cursor.execute("SELECT COUNT(*) FROM treasury")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO treasury (id, total_balance, updated_at)
                VALUES (1, 1000.0, ?)
            """, (datetime.utcnow().isoformat(),))
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenges_verdict ON challenges(verdict_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_challenge ON votes(challenge_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_voter ON votes(voter_wallet)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_wallet ON verification_history(wallet)")


# ==================== CHALLENGE OPERATIONS ====================

def create_challenge(challenge_data: Dict[str, Any]) -> str:
    """Create a new challenge in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO challenges (
                challenge_id, verdict_id, original_claim, original_verdict,
                original_confidence, challenger_wallet, stake_amount,
                evidence_links, explanation, status, voting_deadline, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            challenge_data["challenge_id"],
            challenge_data["verdict_id"],
            challenge_data.get("original_claim"),
            challenge_data.get("original_verdict"),
            challenge_data.get("original_confidence"),
            challenge_data["challenger_wallet"],
            challenge_data["stake_amount"],
            json.dumps(challenge_data["evidence_links"]),
            challenge_data["explanation"],
            challenge_data.get("status", "pending"),
            challenge_data.get("voting_deadline"),
            challenge_data.get("created_at", datetime.utcnow().isoformat())
        ))
        return challenge_data["challenge_id"]


def get_challenge(challenge_id: str) -> Optional[Dict[str, Any]]:
    """Get a challenge by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM challenges WHERE challenge_id = ?", (challenge_id,))
        row = cursor.fetchone()
        if row:
            return _row_to_challenge(row)
        return None


def get_challenges_by_status(status: str) -> List[Dict[str, Any]]:
    """Get all challenges with a specific status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM challenges WHERE status = ? ORDER BY created_at DESC", (status,))
        return [_row_to_challenge(row) for row in cursor.fetchall()]


def get_active_challenges() -> List[Dict[str, Any]]:
    """Get all active challenges (pending or voting)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM challenges 
            WHERE status IN ('pending', 'voting') 
            ORDER BY created_at DESC
        """)
        return [_row_to_challenge(row) for row in cursor.fetchall()]


def get_challenges_by_verdict(verdict_id: str) -> List[Dict[str, Any]]:
    """Get all challenges for a specific verdict."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM challenges WHERE verdict_id = ? ORDER BY created_at DESC", (verdict_id,))
        return [_row_to_challenge(row) for row in cursor.fetchall()]


def update_challenge(challenge_id: str, updates: Dict[str, Any]) -> bool:
    """Update a challenge."""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        # Handle JSON fields
        if "evidence_links" in updates and isinstance(updates["evidence_links"], list):
            updates["evidence_links"] = json.dumps(updates["evidence_links"])
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [challenge_id]
        
        cursor.execute(f"UPDATE challenges SET {set_clause} WHERE challenge_id = ?", values)
        return cursor.rowcount > 0


def _row_to_challenge(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a database row to a challenge dict."""
    data = dict(row)
    if data.get("evidence_links"):
        data["evidence_links"] = json.loads(data["evidence_links"])
    return data


# ==================== VOTE OPERATIONS ====================

def create_vote(vote_data: Dict[str, Any]) -> str:
    """Create a new vote."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO votes (vote_id, challenge_id, voter_wallet, position, weight, reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vote_data["vote_id"],
            vote_data["challenge_id"],
            vote_data["voter_wallet"],
            vote_data["position"],
            vote_data.get("weight", 1.0),
            vote_data.get("reasoning"),
            vote_data.get("created_at", datetime.utcnow().isoformat())
        ))
        return vote_data["vote_id"]


def get_votes_for_challenge(challenge_id: str) -> List[Dict[str, Any]]:
    """Get all votes for a challenge."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM votes WHERE challenge_id = ? ORDER BY created_at", (challenge_id,))
        return [dict(row) for row in cursor.fetchall()]


def has_voted(challenge_id: str, voter_wallet: str) -> bool:
    """Check if a wallet has already voted on a challenge."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM votes WHERE challenge_id = ? AND voter_wallet = ?",
            (challenge_id, voter_wallet)
        )
        return cursor.fetchone()[0] > 0


# ==================== TREASURY OPERATIONS ====================

def get_treasury() -> Dict[str, Any]:
    """Get treasury data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM treasury WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {
            "total_balance": 1000.0,
            "reserved_for_payouts": 0.0,
            "total_challenges": 0,
            "ai_wins": 0,
            "challenger_wins": 0,
            "total_staked_all_time": 0.0,
            "total_paid_out": 0.0
        }


def update_treasury(updates: Dict[str, Any]) -> bool:
    """Update treasury data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        
        cursor.execute(f"UPDATE treasury SET {set_clause} WHERE id = 1", values)
        return cursor.rowcount > 0


def add_treasury_transaction(tx_data: Dict[str, Any]) -> str:
    """Add a treasury transaction record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO treasury_transactions (tx_id, tx_type, amount, challenge_id, wallet, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tx_data["tx_id"],
            tx_data["tx_type"],
            tx_data["amount"],
            tx_data.get("challenge_id"),
            tx_data.get("wallet"),
            tx_data.get("description"),
            tx_data.get("created_at", datetime.utcnow().isoformat())
        ))
        return tx_data["tx_id"]


def get_treasury_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent treasury transactions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM treasury_transactions ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== REPUTATION OPERATIONS ====================

def get_voter_reputation(wallet: str) -> Optional[Dict[str, Any]]:
    """Get voter reputation data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voter_reputation WHERE wallet = ?", (wallet,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get("domain_expertise"):
                data["domain_expertise"] = json.loads(data["domain_expertise"])
            return data
        return None


def create_or_update_reputation(wallet: str, updates: Dict[str, Any]) -> bool:
    """Create or update voter reputation."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT wallet FROM voter_reputation WHERE wallet = ?", (wallet,))
        exists = cursor.fetchone() is not None
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        # Handle JSON fields
        if "domain_expertise" in updates and isinstance(updates["domain_expertise"], dict):
            updates["domain_expertise"] = json.dumps(updates["domain_expertise"])
        
        if exists:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [wallet]
            cursor.execute(f"UPDATE voter_reputation SET {set_clause} WHERE wallet = ?", values)
        else:
            updates["wallet"] = wallet
            updates["created_at"] = datetime.utcnow().isoformat()
            columns = ", ".join(updates.keys())
            placeholders = ", ".join(["?" for _ in updates])
            cursor.execute(f"INSERT INTO voter_reputation ({columns}) VALUES ({placeholders})", list(updates.values()))
        
        return True


def get_top_challengers(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top challengers by total won."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wallet, total_challenges, successful_challenges, total_won
            FROM voter_reputation
            WHERE total_challenges > 0
            ORDER BY total_won DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_top_voters(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top voters by accuracy."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wallet, total_votes, correct_votes, accuracy_rate, reputation
            FROM voter_reputation
            WHERE total_votes >= 5
            ORDER BY accuracy_rate DESC, reputation DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_challenges_by_wallet(wallet: str) -> List[Dict[str, Any]]:
    """Get all challenges submitted by a wallet."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM challenges 
            WHERE challenger_wallet = ?
            ORDER BY created_at DESC
        """, (wallet,))
        return [_row_to_challenge(row) for row in cursor.fetchall()]


def get_verdict(verdict_id: str) -> Optional[Dict[str, Any]]:
    """Get a registered verdict."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM verdicts WHERE verdict_id = ?
        """, (verdict_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def register_verdict(verdict_id: str, claim: str, domain: str, verdict: str, confidence: float) -> bool:
    """Register a verdict for potential challenges."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO verdicts (verdict_id, claim, domain, verdict, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            verdict_id,
            claim,
            domain,
            verdict,
            confidence,
            datetime.utcnow().isoformat()
        ))
        return cursor.rowcount > 0


# ==================== VERIFICATION HISTORY ====================

def save_verification(wallet: Optional[str], verification_data: Dict[str, Any]) -> int:
    """Save a verification to history."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO verification_history (wallet, claim, verdict, confidence, truth_probability, summary, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wallet,
            verification_data.get("claim"),
            verification_data.get("verdict"),
            verification_data.get("confidence"),
            verification_data.get("truth_probability"),
            verification_data.get("summary"),
            json.dumps(verification_data.get("sources", [])),
            datetime.utcnow().isoformat()
        ))
        return cursor.lastrowid


def get_user_history(wallet: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get verification history for a wallet."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM verification_history 
            WHERE wallet = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (wallet, limit))
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get("sources"):
                data["sources"] = json.loads(data["sources"])
            results.append(data)
        return results


# Initialize database on module import
init_database()
