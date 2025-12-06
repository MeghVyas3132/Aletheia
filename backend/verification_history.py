"""
Verification History Storage - Aletheia

Stores all verification results for:
1. User history lookup
2. DOW challenge context
3. Analytics and reporting
4. Audit trail

Uses SQLite for persistence.
"""

import os
import sqlite3
import json
import logging
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class VerificationRecord:
    """A stored verification result."""
    id: str  # Unique verification ID (hash of claim + timestamp)
    claim: str
    verdict: str  # TRUE, FALSE, UNCERTAIN
    confidence: float
    domain: str
    complexity: str
    
    # Detailed results
    council_vote: Dict[str, Any]
    sources: List[str]
    explanation: str
    nuance: str
    
    # Timestamps
    created_at: str
    verification_time_seconds: float
    
    # Optional user info
    user_wallet: Optional[str] = None
    user_ip_hash: Optional[str] = None  # Hashed for privacy
    
    # Challenge info
    challenged: bool = False
    challenge_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VerificationHistoryDB:
    """SQLite-based verification history storage."""
    
    def __init__(self, db_path: str = None):
        # Determine database path with fallbacks
        if db_path:
            self.db_path = db_path
        else:
            default_path = os.path.join(os.path.dirname(__file__), "storage", "verification_history.db")
            self.db_path = os.getenv("VERIFICATION_DB_PATH", default_path)
        
        # Ensure directory exists with fallback
        db_dir = os.path.dirname(self.db_path)
        try:
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        except OSError:
            # Fallback to current directory
            self.db_path = os.path.join(os.path.dirname(__file__), "verification_history.db")
        
        self._init_db()
        logger.info(f"VerificationHistoryDB initialized at {self.db_path}")
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verifications (
                    id TEXT PRIMARY KEY,
                    claim TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    domain TEXT,
                    complexity TEXT,
                    council_vote TEXT,
                    sources TEXT,
                    explanation TEXT,
                    nuance TEXT,
                    created_at TEXT NOT NULL,
                    verification_time_seconds REAL,
                    user_wallet TEXT,
                    user_ip_hash TEXT,
                    challenged INTEGER DEFAULT 0,
                    challenge_id TEXT,
                    
                    -- Full-text search
                    claim_normalized TEXT
                )
            """)
            
            # Indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_verifications_created 
                ON verifications(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_verifications_verdict 
                ON verifications(verdict)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_verifications_user_wallet 
                ON verifications(user_wallet)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_verifications_claim_hash 
                ON verifications(id)
            """)
            
            conn.commit()
    
    def generate_id(self, claim: str) -> str:
        """Generate a unique ID for a verification."""
        timestamp = datetime.now().isoformat()
        hash_input = f"{claim}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def normalize_claim(self, claim: str) -> str:
        """Normalize a claim for duplicate detection."""
        # Lowercase, remove extra whitespace
        normalized = " ".join(claim.lower().split())
        return normalized
    
    def find_similar(self, claim: str, threshold_hours: int = 24) -> Optional[VerificationRecord]:
        """
        Find a similar verification from the last N hours.
        Useful for caching and avoiding duplicate verifications.
        """
        normalized = self.normalize_claim(claim)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM verifications
                WHERE claim_normalized = ?
                AND datetime(created_at) > datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT 1
            """, (normalized, f"-{threshold_hours} hours"))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None
    
    def save(self, record: VerificationRecord) -> str:
        """Save a verification record."""
        normalized = self.normalize_claim(record.claim)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO verifications (
                    id, claim, verdict, confidence, domain, complexity,
                    council_vote, sources, explanation, nuance,
                    created_at, verification_time_seconds,
                    user_wallet, user_ip_hash, challenged, challenge_id,
                    claim_normalized
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.claim,
                record.verdict,
                record.confidence,
                record.domain,
                record.complexity,
                json.dumps(record.council_vote),
                json.dumps(record.sources),
                record.explanation,
                record.nuance,
                record.created_at,
                record.verification_time_seconds,
                record.user_wallet,
                record.user_ip_hash,
                1 if record.challenged else 0,
                record.challenge_id,
                normalized
            ))
            conn.commit()
        
        logger.info(f"Saved verification {record.id}: {record.verdict}")
        return record.id
    
    def get(self, verification_id: str) -> Optional[VerificationRecord]:
        """Get a verification by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM verifications WHERE id = ?",
                (verification_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None
    
    def get_by_wallet(
        self, 
        wallet_address: str, 
        limit: int = 50
    ) -> List[VerificationRecord]:
        """Get verifications for a wallet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM verifications
                WHERE user_wallet = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (wallet_address, limit))
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_recent(self, limit: int = 20) -> List[VerificationRecord]:
        """Get recent verifications."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM verifications
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def search(
        self, 
        query: str, 
        verdict: Optional[str] = None,
        limit: int = 20
    ) -> List[VerificationRecord]:
        """Search verifications by claim text."""
        params = [f"%{query}%"]
        sql = """
            SELECT * FROM verifications
            WHERE claim LIKE ?
        """
        
        if verdict:
            sql += " AND verdict = ?"
            params.append(verdict)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def mark_challenged(self, verification_id: str, challenge_id: str) -> bool:
        """Mark a verification as challenged."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE verifications
                SET challenged = 1, challenge_id = ?
                WHERE id = ?
            """, (challenge_id, verification_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total count
            total = conn.execute(
                "SELECT COUNT(*) FROM verifications"
            ).fetchone()[0]
            
            # By verdict
            by_verdict = {}
            for verdict in ["TRUE", "FALSE", "UNCERTAIN"]:
                count = conn.execute(
                    "SELECT COUNT(*) FROM verifications WHERE verdict = ?",
                    (verdict,)
                ).fetchone()[0]
                by_verdict[verdict] = count
            
            # Challenged count
            challenged = conn.execute(
                "SELECT COUNT(*) FROM verifications WHERE challenged = 1"
            ).fetchone()[0]
            
            # Average confidence
            avg_confidence = conn.execute(
                "SELECT AVG(confidence) FROM verifications"
            ).fetchone()[0] or 0
            
            # Average verification time
            avg_time = conn.execute(
                "SELECT AVG(verification_time_seconds) FROM verifications"
            ).fetchone()[0] or 0
            
            # Last 24 hours
            last_24h = conn.execute("""
                SELECT COUNT(*) FROM verifications
                WHERE datetime(created_at) > datetime('now', '-24 hours')
            """).fetchone()[0]
            
            return {
                "total_verifications": total,
                "by_verdict": by_verdict,
                "challenged_count": challenged,
                "challenge_rate": (challenged / total * 100) if total > 0 else 0,
                "average_confidence": round(avg_confidence, 2),
                "average_verification_time": round(avg_time, 2),
                "last_24_hours": last_24h
            }
    
    def _row_to_record(self, row: sqlite3.Row) -> VerificationRecord:
        """Convert a database row to a VerificationRecord."""
        return VerificationRecord(
            id=row["id"],
            claim=row["claim"],
            verdict=row["verdict"],
            confidence=row["confidence"],
            domain=row["domain"],
            complexity=row["complexity"],
            council_vote=json.loads(row["council_vote"]) if row["council_vote"] else {},
            sources=json.loads(row["sources"]) if row["sources"] else [],
            explanation=row["explanation"],
            nuance=row["nuance"],
            created_at=row["created_at"],
            verification_time_seconds=row["verification_time_seconds"],
            user_wallet=row["user_wallet"],
            user_ip_hash=row["user_ip_hash"],
            challenged=bool(row["challenged"]),
            challenge_id=row["challenge_id"]
        )


# Singleton instance
_history_db: Optional[VerificationHistoryDB] = None


def get_history_db() -> VerificationHistoryDB:
    """Get the singleton verification history database."""
    global _history_db
    if _history_db is None:
        _history_db = VerificationHistoryDB()
    return _history_db


def create_verification_record(
    claim: str,
    verdict: str,
    confidence: float,
    domain: str,
    complexity: str,
    council_vote: Dict[str, Any],
    sources: List[str],
    explanation: str,
    nuance: str,
    verification_time: float,
    user_wallet: Optional[str] = None,
    user_ip: Optional[str] = None
) -> VerificationRecord:
    """
    Create a verification record from verification results.
    
    This is a helper function to create records from API response data.
    """
    db = get_history_db()
    
    # Hash IP for privacy
    ip_hash = None
    if user_ip:
        ip_hash = hashlib.sha256(user_ip.encode()).hexdigest()[:12]
    
    record = VerificationRecord(
        id=db.generate_id(claim),
        claim=claim,
        verdict=verdict,
        confidence=confidence,
        domain=domain,
        complexity=complexity,
        council_vote=council_vote,
        sources=sources,
        explanation=explanation,
        nuance=nuance or "",
        created_at=datetime.now().isoformat(),
        verification_time_seconds=verification_time,
        user_wallet=user_wallet,
        user_ip_hash=ip_hash
    )
    
    return record
