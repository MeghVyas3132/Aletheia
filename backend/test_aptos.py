"""
Test script for Aptos blockchain integration.
"""

import os
import time
from blockchain import (
    SyncAptosVerdictClient,
    submit_verdict_to_chain,
    check_verdict_exists,
)


def test_connection():
    """Test connection to Aptos testnet."""
    print("🔗 Testing Aptos Testnet Connection...")
    
    client = SyncAptosVerdictClient()
    total = client.get_total_verdicts()
    print(f"   ✓ Connected! Total verdicts on-chain: {total}")
    return True


def test_submit_verdict():
    """Test submitting a verdict to the blockchain."""
    print("\n📝 Testing Verdict Submission...")
    
    # Use unique claim hash with timestamp
    unique_hash = f"test_claim_{int(time.time())}"
    
    # Sample chain_metadata (similar to what TheJudge produces)
    test_metadata = {
        "claim_hash": unique_hash,
        "claim_signature": "test_sig_abc",
        "keywords": ["test", "blockchain", "moveh"],
        "claim_type": 2,  # BREAKING_NEWS
        "timestamp_unix": 1704067200,
        "expires_at": 1704672000,
    }
    
    tx_hash = submit_verdict_to_chain(
        chain_metadata=test_metadata,
        shelby_cid="bafybeigdyrzttest",
        verdict="TRUE",
        confidence=85,
    )
    
    if tx_hash:
        print(f"   ✓ Transaction submitted!")
        print(f"   TX Hash: {tx_hash}")
        print(f"   Explorer: https://explorer.aptoslabs.com/txn/{tx_hash}?network=testnet")
        return unique_hash
    else:
        print("   ✗ Transaction failed")
        return None


def test_verdict_exists(claim_hash: str = "test_claim_hash_123456789"):
    """Test checking if verdict exists."""
    print(f"\n🔍 Testing Verdict Lookup for: {claim_hash[:30]}...")
    
    exists = check_verdict_exists(claim_hash)
    print(f"   Verdict exists: {exists}")
    return exists


def test_get_verdict(claim_hash: str = "test_claim_hash_123456789"):
    """Test retrieving a verdict."""
    print(f"\n📖 Testing Verdict Retrieval for: {claim_hash[:30]}...")
    
    client = SyncAptosVerdictClient()
    record = client.get_verdict(claim_hash)
    
    if record:
        print(f"   ✓ Verdict found!")
        print(f"   Claim Hash: {record.claim_hash}")
        print(f"   Verdict: {client._async_client.verdict_int_to_string(record.verdict)}")
        print(f"   Confidence: {record.confidence}%")
        print(f"   Shelby CID: {record.shelby_cid}")
        return record
    else:
        print("   ✗ Verdict not found")
        return None


def main():
    """Run all tests."""
    print("=" * 50)
    print("🧪 MoveH Aptos Integration Tests")
    print("=" * 50)
    
    # Test 1: Connection
    # If APTOS_PRIVATE_KEY is not set, skip integration tests
    if not os.getenv("APTOS_PRIVATE_KEY"):
        print("⚠️  APTOS_PRIVATE_KEY not set — skipping Aptos integration tests.")
        print("   To run these tests, export APTOS_PRIVATE_KEY or run with a local .aptos/config.yaml containing the private key (unsafe to commit)")
        return

    test_connection()
    
    # Test 2: Submit verdict (returns unique claim hash)
    claim_hash = test_submit_verdict()
    
    if claim_hash:
        # Test 3: Check exists
        test_verdict_exists(claim_hash)
        
        # Test 4: Get verdict
        test_get_verdict(claim_hash)
    
    print("\n" + "=" * 50)
    print("✅ Tests Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
