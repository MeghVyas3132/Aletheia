"""
Aptos Blockchain Client for MoveH

Python wrapper for interacting with the VerdictRegistry smart contract on Aptos.
Handles verdict submission, retrieval, and deduplication checks.
"""

import os
import time
import json
from typing import Optional
from dataclasses import dataclass
from enum import IntEnum

from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient, ClientConfig
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionArgument,
    TransactionPayload,
)
from aptos_sdk.bcs import Serializer
import asyncio


class VerdictValue(IntEnum):
    """On-chain verdict values matching Move contract."""
    TRUE = 1
    FALSE = 2
    PARTIALLY_TRUE = 3
    UNVERIFIABLE = 4


@dataclass
class VerdictRecord:
    """Python representation of on-chain VerdictRecord."""
    claim_hash: str
    claim_signature: str
    keywords: list[str]
    claim_type: int
    verdict: int
    confidence: int
    shelby_cid: str
    timestamp: int
    expiry: int
    submitter: str


class AptosVerdictClient:
    """
    Client for interacting with the MoveH VerdictRegistry on Aptos Testnet.
    
    Usage:
        client = AptosVerdictClient()
        
        # Check if verdict already exists (deduplication)
        exists = await client.verdict_exists("abc123...")
        
        # Submit new verdict
        tx_hash = await client.submit_verdict(chain_metadata, shelby_cid)
        
        # Retrieve verdict
        record = await client.get_verdict("abc123...")
    """
    
    # Contract configuration
    MODULE_NAME = "verdict_registry"
    REST_URL = "https://fullnode.testnet.aptoslabs.com/v1"
    
    def __init__(
        self, 
        private_key: Optional[str] = None, 
        module_address: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the Aptos client.
        
        Args:
            private_key: Hex-encoded private key. If None, reads from APTOS_PRIVATE_KEY env var.
            module_address: Contract address. If None, reads from APTOS_MODULE_ADDRESS env var.
            api_key: Geomi API key for higher rate limits. Get one at https://geomi.dev/
        
        Raises:
            ValueError: If private_key or module_address not provided and not in environment.
        """
        # Get private key from parameter or environment
        key = private_key or os.getenv("APTOS_PRIVATE_KEY")
        if not key:
            raise ValueError(
                "APTOS_PRIVATE_KEY must be set in environment or passed as parameter. "
                "Never hardcode private keys in source code!"
            )
        
        # Get module address from parameter or environment
        self.MODULE_ADDRESS = module_address or os.getenv("APTOS_MODULE_ADDRESS")
        if not self.MODULE_ADDRESS:
            raise ValueError(
                "APTOS_MODULE_ADDRESS must be set in environment or passed as parameter."
            )
        # Remove 'ed25519-priv-' prefix if present
        if key.startswith("ed25519-priv-"):
            key = key.replace("ed25519-priv-", "")
        
        self.account = Account.load_key(key)
        
        # Use Geomi API key if provided (removes rate limiting)
        geomi_api_key = api_key or os.getenv("GEOMI_API_KEY")
        if geomi_api_key:
            config = ClientConfig(api_key=geomi_api_key)
            self.client = RestClient(self.REST_URL, config)
            print(f"[Aptos] Using Geomi API key for higher rate limits")
        else:
            self.client = RestClient(self.REST_URL)
            print(f"[Aptos] Warning: No API key - subject to rate limits. Get one at https://geomi.dev/")
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()
    
    def _parse_view_result(self, result: bytes) -> list:
        """Parse bytes result from view function into Python objects."""
        if isinstance(result, bytes):
            return json.loads(result.decode('utf-8'))
        return result if result else []
    
    @staticmethod
    def verdict_string_to_int(verdict: str) -> int:
        """Convert verdict string to on-chain integer value."""
        mapping = {
            "TRUE": VerdictValue.TRUE,
            "PROBABLY_TRUE": VerdictValue.PARTIALLY_TRUE,  # Map to PARTIALLY_TRUE
            "UNCERTAIN": VerdictValue.UNVERIFIABLE,        # Map to UNVERIFIABLE
            "PROBABLY_FALSE": VerdictValue.PARTIALLY_TRUE, # Map to PARTIALLY_TRUE
            "FALSE": VerdictValue.FALSE,
        }
        return mapping.get(verdict.upper(), VerdictValue.UNVERIFIABLE)
    
    @staticmethod
    def verdict_int_to_string(verdict: int) -> str:
        """Convert on-chain integer to verdict string."""
        mapping = {
            1: "TRUE",
            2: "FALSE",
            3: "PARTIALLY_TRUE",
            4: "UNVERIFIABLE",
        }
        return mapping.get(verdict, "UNVERIFIABLE")
    
    async def verdict_exists(self, claim_hash: str) -> bool:
        """
        Check if a verdict already exists on-chain for this claim hash.
        Useful for deduplication before running expensive agents.
        
        Args:
            claim_hash: The claim hash to check.
            
        Returns:
            True if verdict exists, False otherwise.
        """
        try:
            function = f"{self.MODULE_ADDRESS}::{self.MODULE_NAME}::verdict_exists"
            result = await self.client.view(function, [], [claim_hash])
            parsed = self._parse_view_result(result)
            return parsed[0] if parsed else False
        except Exception as e:
            print(f"[Aptos] Error checking verdict existence: {e}")
            return False
    
    async def is_verdict_fresh(self, claim_hash: str) -> bool:
        """
        Check if an existing verdict is still fresh (not expired).
        
        Args:
            claim_hash: The claim hash to check.
            
        Returns:
            True if verdict is fresh, False if expired or doesn't exist.
        """
        try:
            function = f"{self.MODULE_ADDRESS}::{self.MODULE_NAME}::is_verdict_fresh"
            result = await self.client.view(function, [], [claim_hash])
            parsed = self._parse_view_result(result)
            return parsed[0] if parsed else False
        except Exception:
            return False
    
    async def get_verdict(self, claim_hash: str) -> Optional[VerdictRecord]:
        """
        Retrieve a verdict from the blockchain.
        
        Args:
            claim_hash: The claim hash to look up.
            
        Returns:
            VerdictRecord if found, None otherwise.
        """
        try:
            function = f"{self.MODULE_ADDRESS}::{self.MODULE_NAME}::get_verdict"
            result = await self.client.view(function, [], [claim_hash])
            parsed = self._parse_view_result(result)
            
            # Result is a list: [verdict, confidence, shelby_cid, timestamp, expiry, is_fresh]
            if parsed and len(parsed) >= 6:
                return VerdictRecord(
                    claim_hash=claim_hash,
                    claim_signature="",  # Not returned by view function
                    keywords=[],  # Not returned by view function
                    claim_type=0,  # Not returned by view function
                    verdict=int(parsed[0]),
                    confidence=int(parsed[1]),
                    shelby_cid=str(parsed[2]),
                    timestamp=int(parsed[3]),
                    expiry=int(parsed[4]),
                    submitter="",  # Not returned by view function
                )
            return None
        except Exception as e:
            print(f"[Aptos] Error retrieving verdict: {e}")
            return None
    
    async def get_total_verdicts(self) -> int:
        """Get total number of verdicts stored on-chain."""
        try:
            function = f"{self.MODULE_ADDRESS}::{self.MODULE_NAME}::get_total_verdicts"
            result = await self.client.view(function, [], [])
            parsed = self._parse_view_result(result)
            return int(parsed[0]) if parsed else 0
        except Exception:
            return 0
    
    async def submit_verdict(
        self,
        chain_metadata: dict,
        shelby_cid: str,
        verdict: str,
        confidence: int,
    ) -> Optional[str]:
        """
        Submit a verdict to the blockchain.
        
        Args:
            chain_metadata: The chain_metadata dict from AEP package containing:
                - claim_hash: str
                - claim_signature: str  
                - keywords: list[str]
                - claim_type: int
                - timestamp_unix: int
                - expires_at: int
            shelby_cid: The Shelby IPFS CID for full report storage.
            verdict: Verdict string (TRUE, FALSE, PROBABLY_TRUE, etc.)
            confidence: Confidence percentage (0-100).
            
        Returns:
            Transaction hash if successful, None otherwise.
        """
        try:
            # Extract metadata
            claim_hash = chain_metadata.get("claim_hash", "")[:64]  # Max 64 chars
            claim_signature = chain_metadata.get("claim_signature", "")[:32]  # Max 32 chars
            keywords = chain_metadata.get("keywords", [])[:10]  # Max 10 keywords
            claim_type = chain_metadata.get("claim_type", 2)  # Default BREAKING_NEWS
            expiry = chain_metadata.get("expires_at", 0)
            
            # Convert verdict to integer
            verdict_int = self.verdict_string_to_int(verdict)
            
            # Ensure confidence is in valid range
            confidence = max(0, min(100, confidence))
            
            # Build transaction payload
            payload = EntryFunction.natural(
                f"{self.MODULE_ADDRESS}::{self.MODULE_NAME}",
                "submit_verdict",
                [],  # Type arguments
                [
                    TransactionArgument(claim_hash, Serializer.str),
                    TransactionArgument(claim_signature, Serializer.str),
                    TransactionArgument(keywords, Serializer.sequence_serializer(Serializer.str)),
                    TransactionArgument(claim_type, Serializer.u8),
                    TransactionArgument(verdict_int, Serializer.u8),
                    TransactionArgument(confidence, Serializer.u8),  # u8 per Move contract
                    TransactionArgument(shelby_cid, Serializer.str),
                    TransactionArgument(expiry, Serializer.u64),
                ],
            )
            
            # Sign and submit transaction
            signed_txn = await self.client.create_bcs_signed_transaction(
                self.account,
                TransactionPayload(payload),
            )
            
            tx_hash = await self.client.submit_bcs_transaction(signed_txn)
            
            # Wait for transaction confirmation
            await self.client.wait_for_transaction(tx_hash)
            
            print(f"[Aptos] ✓ Verdict submitted! TX: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            print(f"[Aptos] ✗ Error submitting verdict: {e}")
            return None
    
    async def search_by_keyword(self, keyword: str) -> list[str]:
        """
        Search for claim hashes by keyword.
        
        Args:
            keyword: The keyword to search for.
            
        Returns:
            List of claim hashes matching the keyword.
        """
        try:
            function = f"{self.MODULE_ADDRESS}::{self.MODULE_NAME}::get_hashes_by_keyword"
            result = await self.client.view(function, [], [keyword])
            parsed = self._parse_view_result(result)
            # Result is [[hash1, hash2, ...]], so return the inner list
            return parsed[0] if parsed and len(parsed) > 0 else []
        except Exception:
            return []


# Synchronous wrapper for easier integration
class SyncAptosVerdictClient:
    """
    Synchronous wrapper around AptosVerdictClient.
    
    Usage:
        client = SyncAptosVerdictClient()
        exists = client.verdict_exists("abc123...")
        tx_hash = client.submit_verdict(chain_metadata, shelby_cid, verdict, confidence)
    """
    
    def __init__(self, private_key: Optional[str] = None):
        self._async_client = AptosVerdictClient(private_key)
        
    def _run(self, coro):
        """Run async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    def verdict_exists(self, claim_hash: str) -> bool:
        return self._run(self._async_client.verdict_exists(claim_hash))
    
    def is_verdict_fresh(self, claim_hash: str) -> bool:
        return self._run(self._async_client.is_verdict_fresh(claim_hash))
    
    def get_verdict(self, claim_hash: str) -> Optional[VerdictRecord]:
        return self._run(self._async_client.get_verdict(claim_hash))
    
    def get_total_verdicts(self) -> int:
        return self._run(self._async_client.get_total_verdicts())
    
    def submit_verdict(
        self,
        chain_metadata: dict,
        shelby_cid: str,
        verdict: str,
        confidence: int,
    ) -> Optional[str]:
        return self._run(
            self._async_client.submit_verdict(chain_metadata, shelby_cid, verdict, confidence)
        )
    
    def search_by_keyword(self, keyword: str) -> list[str]:
        return self._run(self._async_client.search_by_keyword(keyword))


def submit_verdict_to_chain(
    chain_metadata: dict,
    shelby_cid: str,
    verdict: str,
    confidence: int,
) -> Optional[str]:
    """
    Convenience function to submit verdict to blockchain.
    
    Args:
        chain_metadata: The chain_metadata dict from AEP package.
        shelby_cid: The Shelby IPFS CID for full report storage.
        verdict: Verdict string (TRUE, FALSE, PROBABLY_TRUE, etc.)
        confidence: Confidence percentage (0-100).
        
    Returns:
        Transaction hash if successful, None otherwise.
        
    Example:
        tx_hash = submit_verdict_to_chain(
            aep["chain_metadata"],
            "bafybeiabc123...",
            "FALSE",
            85
        )
    """
    client = SyncAptosVerdictClient()
    return client.submit_verdict(chain_metadata, shelby_cid, verdict, confidence)


def check_verdict_exists(claim_hash: str) -> bool:
    """
    Convenience function to check if verdict exists on-chain.
    
    Args:
        claim_hash: The claim hash to check.
        
    Returns:
        True if verdict exists, False otherwise.
    """
    client = SyncAptosVerdictClient()
    return client.verdict_exists(claim_hash)


def get_verdict_from_chain(claim_hash: str) -> Optional[VerdictRecord]:
    """
    Convenience function to retrieve verdict from blockchain.
    
    Args:
        claim_hash: The claim hash to look up.
        
    Returns:
        VerdictRecord if found, None otherwise.
    """
    client = SyncAptosVerdictClient()
    return client.get_verdict(claim_hash)
