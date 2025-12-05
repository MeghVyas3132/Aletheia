"""
Chain Lookup Service for MoveH

Searches the blockchain for existing verdicts before running agents.
Implements the deduplication flow:
1. Extract keywords from query
2. Search chain for matching verdicts
3. Filter & rank by relevance
4. Check freshness
5. Return cached or trigger re-verification
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from blockchain.aptos_client import SyncAptosVerdictClient, VerdictRecord

load_dotenv()


@dataclass
class CachedVerdict:
    """A cached verdict from the blockchain."""
    claim_hash: str
    verdict: str
    confidence: int
    shelby_cid: str
    is_fresh: bool
    relevance_score: float
    timestamp: int
    keywords_matched: list[str]


class ChainLookupService:
    """
    Service to lookup existing verdicts on-chain before running agents.
    
    Usage:
        lookup = ChainLookupService()
        result = lookup.find_existing_verdict("Did Tesla acquire Twitter?")
        
        if result and result.is_fresh:
            print(f"Found cached verdict: {result.verdict}")
        else:
            # Run full agent pipeline
            ...
    """
    
    def __init__(self):
        self.client = SyncAptosVerdictClient()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.1,
        )
    
    def extract_keywords(self, query: str) -> list[str]:
        """
        Step 1: Extract searchable keywords from user query using LLM.
        
        Args:
            query: The user's claim/question
            
        Returns:
            List of keywords for blockchain search
        """
        prompt = f"""Extract 3-5 search keywords from this claim for fact-checking lookup.
Return ONLY lowercase keywords separated by commas, no explanations.

Claim: "{query}"

Keywords:"""

        response = self.llm.invoke([
            SystemMessage(content="You extract search keywords. Return only comma-separated lowercase words."),
            HumanMessage(content=prompt)
        ])
        
        # Parse keywords
        keywords_str = response.content.strip()
        keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
        
        # Limit to 5 keywords
        return keywords[:5]
    
    def search_chain_by_keywords(self, keywords: list[str]) -> list[tuple[str, str]]:
        """
        Step 2: Search blockchain for verdicts matching keywords.
        
        Args:
            keywords: List of keywords to search
            
        Returns:
            List of (claim_hash, keyword) tuples
        """
        results = []
        seen_hashes = set()
        
        for keyword in keywords:
            try:
                hashes = self.client.search_by_keyword(keyword)
                for h in hashes:
                    if h not in seen_hashes:
                        results.append((h, keyword))
                        seen_hashes.add(h)
            except Exception as e:
                print(f"[ChainLookup] Error searching keyword '{keyword}': {e}")
                continue
        
        return results
    
    def get_verdict_details(self, claim_hash: str) -> Optional[VerdictRecord]:
        """Get full verdict details from chain."""
        try:
            return self.client.get_verdict(claim_hash)
        except Exception:
            return None
    
    def rank_by_relevance(
        self, 
        query: str, 
        candidates: list[tuple[str, VerdictRecord, str]]
    ) -> list[tuple[str, VerdictRecord, str, float]]:
        """
        Step 3: Rank candidates by semantic relevance to the query.
        
        Args:
            query: Original user query
            candidates: List of (claim_hash, verdict_record, matched_keyword)
            
        Returns:
            List of (claim_hash, verdict_record, matched_keyword, relevance_score) sorted by relevance
        """
        if not candidates:
            return []
        
        if len(candidates) == 1:
            # Only one candidate, give it a default high score
            h, record, kw = candidates[0]
            return [(h, record, kw, 0.8)]
        
        # Build prompt for LLM to rank
        candidate_list = "\n".join([
            f"{i+1}. Hash: {h[:16]}..., Keywords matched: {kw}, Shelby CID: {record.shelby_cid}"
            for i, (h, record, kw) in enumerate(candidates)
        ])
        
        prompt = f"""Given this user query and candidate verdicts, rate each candidate's relevance from 0.0 to 1.0.

User Query: "{query}"

Candidates:
{candidate_list}

Return ONLY a comma-separated list of scores in order (e.g., "0.9, 0.3, 0.7"):"""

        try:
            response = self.llm.invoke([
                SystemMessage(content="You rate relevance. Return only comma-separated decimal scores."),
                HumanMessage(content=prompt)
            ])
            
            scores_str = response.content.strip()
            scores = [float(s.strip()) for s in scores_str.split(",")]
            
            # Pair with candidates
            ranked = []
            for i, (h, record, kw) in enumerate(candidates):
                score = scores[i] if i < len(scores) else 0.5
                ranked.append((h, record, kw, score))
            
            # Sort by relevance descending
            ranked.sort(key=lambda x: x[3], reverse=True)
            return ranked
            
        except Exception as e:
            print(f"[ChainLookup] Error ranking: {e}")
            # Return with default scores
            return [(h, record, kw, 0.5) for h, record, kw in candidates]
    
    def check_freshness(self, claim_hash: str) -> bool:
        """
        Step 4: Check if verdict is still fresh (not expired).
        
        Args:
            claim_hash: The claim hash to check
            
        Returns:
            True if fresh, False if stale
        """
        try:
            return self.client.is_verdict_fresh(claim_hash)
        except Exception:
            return False
    
    def find_existing_verdict(self, query: str) -> Optional[CachedVerdict]:
        """
        Main entry point: Find an existing verdict for the given query.
        
        This implements the full flow:
        1. Extract keywords
        2. Search chain
        3. Get verdict details
        4. Rank by relevance
        5. Check freshness
        
        Args:
            query: The user's claim/question
            
        Returns:
            CachedVerdict if found and relevant, None otherwise
        """
        print(f"\n[ChainLookup] 🔍 Searching blockchain for existing verdicts...")
        
        # Step 1: Extract keywords
        keywords = self.extract_keywords(query)
        print(f"[ChainLookup] Keywords: {keywords}")
        
        if not keywords:
            print("[ChainLookup] No keywords extracted")
            return None
        
        # Step 2: Search chain
        matches = self.search_chain_by_keywords(keywords)
        print(f"[ChainLookup] Found {len(matches)} potential matches")
        
        if not matches:
            print("[ChainLookup] No matches found on chain")
            return None
        
        # Step 3: Get verdict details for each match
        candidates = []
        for claim_hash, matched_keyword in matches:
            record = self.get_verdict_details(claim_hash)
            if record:
                candidates.append((claim_hash, record, matched_keyword))
        
        if not candidates:
            print("[ChainLookup] Could not retrieve verdict details")
            return None
        
        # Step 4: Rank by relevance
        ranked = self.rank_by_relevance(query, candidates)
        
        if not ranked:
            return None
        
        # Get best match
        best_hash, best_record, best_keyword, relevance = ranked[0]
        
        # Only accept if relevance is high enough
        if relevance < 0.6:
            print(f"[ChainLookup] Best match relevance too low: {relevance:.2f}")
            return None
        
        print(f"[ChainLookup] Best match: {best_hash[:16]}... (relevance: {relevance:.2f})")
        
        # Step 5: Check freshness
        is_fresh = self.check_freshness(best_hash)
        
        # Convert verdict int to string
        verdict_str = self.client._async_client.verdict_int_to_string(best_record.verdict)
        
        return CachedVerdict(
            claim_hash=best_hash,
            verdict=verdict_str,
            confidence=best_record.confidence,
            shelby_cid=best_record.shelby_cid,
            is_fresh=is_fresh,
            relevance_score=relevance,
            timestamp=best_record.timestamp,
            keywords_matched=[best_keyword],
        )


def lookup_cached_verdict(query: str) -> Optional[CachedVerdict]:
    """
    Convenience function to lookup a cached verdict.
    
    Args:
        query: The claim to check
        
    Returns:
        CachedVerdict if found, None otherwise
    """
    service = ChainLookupService()
    return service.find_existing_verdict(query)
