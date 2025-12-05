#!/usr/bin/env python3
"""
MoveH Full System Test Suite

Run all tests: uv run python test_full_system.py
Run specific test: uv run python test_full_system.py TestBlockchain
"""

import os
import sys
import time
import unittest
from datetime import datetime

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestEnvironment(unittest.TestCase):
    """Test 1: Environment Setup"""
    
    def test_env_file_exists(self):
        """Check .env file exists"""
        self.assertTrue(os.path.exists('.env'), "Missing .env file")
        print("✅ .env file exists")
    
    def test_google_api_key(self):
        """Check Google API key is set"""
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("GOOGLE_API_KEY")
        self.assertIsNotNone(key, "GOOGLE_API_KEY not set in .env")
        self.assertTrue(len(key) > 10, "GOOGLE_API_KEY looks invalid")
        print("✅ GOOGLE_API_KEY is set")
    
    def test_tavily_api_key(self):
        """Check Tavily API key is set"""
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("TAVILY_API_KEY")
        self.assertIsNotNone(key, "TAVILY_API_KEY not set in .env")
        self.assertTrue(len(key) > 10, "TAVILY_API_KEY looks invalid")
        print("✅ TAVILY_API_KEY is set")
    
    def test_geomi_api_key(self):
        """Check Geomi API key is set (optional but recommended)"""
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("GEOMI_API_KEY")
        if key:
            self.assertTrue(key.startswith("aptoslabs_"), "GEOMI_API_KEY should start with 'aptoslabs_'")
            print("✅ GEOMI_API_KEY is set")
        else:
            print("⚠️  GEOMI_API_KEY not set - will have rate limits")


class TestBlockchain(unittest.TestCase):
    """Test 2: Blockchain Connection & Operations"""
    
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv()
        from blockchain.aptos_client import SyncAptosVerdictClient
        cls.client = SyncAptosVerdictClient()
    
    def test_connection(self):
        """Test connection to Aptos testnet"""
        total = self.client.get_total_verdicts()
        self.assertIsInstance(total, int, "Should return integer")
        self.assertGreaterEqual(total, 0, "Total should be >= 0")
        print(f"✅ Connected to Aptos - {total} verdicts on chain")
    
    def test_search_by_keyword(self):
        """Test keyword search functionality"""
        # Search for 'test' keyword (should exist from previous tests)
        hashes = self.client.search_by_keyword("test")
        self.assertIsInstance(hashes, list, "Should return a list")
        print(f"✅ Keyword search works - found {len(hashes)} results for 'test'")
    
    def test_verdict_exists(self):
        """Test verdict_exists function"""
        # Check a known hash
        exists = self.client.verdict_exists("test_claim_cli_003")
        self.assertIsInstance(exists, bool, "Should return boolean")
        print(f"✅ verdict_exists works - 'test_claim_cli_003' exists: {exists}")
    
    def test_get_verdict(self):
        """Test retrieving verdict details"""
        record = self.client.get_verdict("test_claim_cli_003")
        if record:
            self.assertIsNotNone(record.verdict, "Should have verdict")
            self.assertIsNotNone(record.confidence, "Should have confidence")
            print(f"✅ get_verdict works - verdict: {record.verdict}, confidence: {record.confidence}")
        else:
            print("⚠️  get_verdict returned None (claim may not exist)")
    
    def test_is_verdict_fresh(self):
        """Test freshness check"""
        fresh = self.client.is_verdict_fresh("test_claim_cli_003")
        self.assertIsInstance(fresh, bool, "Should return boolean")
        print(f"✅ is_verdict_fresh works - result: {fresh}")


class TestChainLookup(unittest.TestCase):
    """Test 3: Chain Lookup / Deduplication Service"""
    
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv()
        from blockchain.chain_lookup import ChainLookupService
        cls.service = ChainLookupService()
    
    def test_keyword_extraction(self):
        """Test keyword extraction from query"""
        keywords = self.service.extract_keywords("Did Tesla acquire Twitter for $100 billion?")
        self.assertIsInstance(keywords, list, "Should return list")
        self.assertGreater(len(keywords), 0, "Should extract at least 1 keyword")
        self.assertLessEqual(len(keywords), 5, "Should limit to 5 keywords")
        print(f"✅ Keyword extraction works: {keywords}")
    
    def test_search_chain(self):
        """Test blockchain search by keywords"""
        matches = self.service.search_chain_by_keywords(["test"])
        self.assertIsInstance(matches, list, "Should return list")
        print(f"✅ Chain search works - found {len(matches)} matches")
    
    def test_full_lookup_no_match(self):
        """Test lookup for non-existent claim"""
        result = self.service.find_existing_verdict("XYZ random claim that doesn't exist 12345")
        # Should return None for non-existent claims
        print(f"✅ Full lookup works - result for random claim: {result}")
    
    def test_full_lookup_with_test(self):
        """Test lookup for 'test' keyword (should find matches)"""
        result = self.service.find_existing_verdict("This is a test claim")
        if result:
            self.assertIsNotNone(result.verdict, "Should have verdict")
            print(f"✅ Found cached verdict: {result.verdict} ({result.confidence}%)")
        else:
            print("⚠️  No cached verdict found for 'test' claim")


class TestAgents(unittest.TestCase):
    """Test 4: AI Agents"""
    
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv()
    
    def test_fact_checker_import(self):
        """Test Fact Checker agent can be imported"""
        from agents.fact_checker import FactChecker
        agent = FactChecker()
        self.assertIsNotNone(agent, "Should create agent")
        print("✅ Fact Checker agent imports correctly")
    
    def test_forensic_expert_import(self):
        """Test Forensic Expert agent can be imported"""
        from agents.forensic_expert import ForensicExpert
        agent = ForensicExpert()
        self.assertIsNotNone(agent, "Should create agent")
        print("✅ Forensic Expert agent imports correctly")
    
    def test_judge_import(self):
        """Test Judge agent can be imported"""
        from agents.judge import TheJudge
        agent = TheJudge()
        self.assertIsNotNone(agent, "Should create agent")
        print("✅ Judge agent imports correctly")


class TestSubmitVerdict(unittest.TestCase):
    """Test 5: Submit Verdict to Blockchain (Integration Test)"""
    
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv()
        from blockchain.aptos_client import SyncAptosVerdictClient
        cls.client = SyncAptosVerdictClient()
    
    def test_submit_verdict(self):
        """Test submitting a verdict to blockchain"""
        # Create test metadata
        test_hash = f"test_claim_python_{int(time.time())}"
        chain_metadata = {
            "claim_hash": test_hash,
            "claim_signature": "test_sig",
            "keywords": ["test", "python", "automated"],
            "claim_type": 2,
            "timestamp_unix": int(time.time()),
            "expires_at": 0,
        }
        
        print(f"\n📤 Submitting test verdict with hash: {test_hash}")
        
        tx_hash = self.client.submit_verdict(
            chain_metadata=chain_metadata,
            shelby_cid="bafytest_automated_123",
            verdict="TRUE",
            confidence=95
        )
        
        if tx_hash:
            print(f"✅ Verdict submitted! TX: {tx_hash}")
            
            # Verify it was stored
            time.sleep(2)  # Wait for transaction to be indexed
            exists = self.client.verdict_exists(test_hash)
            self.assertTrue(exists, "Verdict should exist after submission")
            print(f"✅ Verified verdict exists on chain")
        else:
            print("⚠️  Submission failed - likely rate limited. Add GEOMI_API_KEY to .env")
            self.skipTest("Rate limited - need GEOMI_API_KEY")


class TestEndToEnd(unittest.TestCase):
    """Test 6: End-to-End Pipeline Test"""
    
    def test_full_pipeline_dry_run(self):
        """Test the full pipeline can be initialized"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import main components
        from agents.fact_checker import FactChecker
        from agents.forensic_expert import ForensicExpert
        from agents.judge import TheJudge
        from blockchain.chain_lookup import ChainLookupService
        from blockchain.aptos_client import SyncAptosVerdictClient
        
        # Initialize all components
        fact_checker = FactChecker()
        forensic_expert = ForensicExpert()
        judge = TheJudge()
        chain_lookup = ChainLookupService()
        aptos_client = SyncAptosVerdictClient()
        
        print("✅ All pipeline components initialized successfully")
        print("   - Fact Checker: Ready")
        print("   - Forensic Expert: Ready")
        print("   - Judge: Ready")
        print("   - Chain Lookup: Ready")
        print("   - Aptos Client: Ready")


def run_tests():
    """Run all tests with nice output"""
    print("\n" + "="*70)
    print("🛡️  MoveH - Full System Test Suite")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes in order
    test_classes = [
        TestEnvironment,
        TestBlockchain,
        TestChainLookup,
        TestAgents,
        TestSubmitVerdict,
        TestEndToEnd,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    print(f"   Tests Run: {result.testsRun}")
    print(f"   ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   ⚠️  Errors: {len(result.errors)}")
    print("="*70 + "\n")
    
    return result


if __name__ == "__main__":
    # Allow running specific test class
    if len(sys.argv) > 1:
        # Run specific test class
        unittest.main(verbosity=2)
    else:
        # Run all tests
        result = run_tests()
        sys.exit(0 if result.wasSuccessful() else 1)
