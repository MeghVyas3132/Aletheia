"""
MoveH Blockchain Module

Aptos Move smart contract integration for on-chain fact verification.
"""

from blockchain.aptos_client import (
    AptosVerdictClient,
    SyncAptosVerdictClient,
    VerdictRecord,
    VerdictValue,
    submit_verdict_to_chain,
    check_verdict_exists,
    get_verdict_from_chain,
)

from blockchain.chain_lookup import (
    ChainLookupService,
    CachedVerdict,
    lookup_cached_verdict,
)

__all__ = [
    # Aptos Client
    "AptosVerdictClient",
    "SyncAptosVerdictClient", 
    "VerdictRecord",
    "VerdictValue",
    "submit_verdict_to_chain",
    "check_verdict_exists",
    "get_verdict_from_chain",
    # Chain Lookup
    "ChainLookupService",
    "CachedVerdict",
    "lookup_cached_verdict",
]
