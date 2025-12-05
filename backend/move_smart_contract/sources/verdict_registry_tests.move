// Tests for MoveH Verdict Registry
#[test_only]
module moveh::verdict_registry_tests {
    use std::string;
    use std::vector;
    use aptos_framework::account;
    use aptos_framework::timestamp;
    use moveh::verdict_registry;

    // Test constants
    const VERDICT_TRUE: u8 = 1;
    const VERDICT_FALSE: u8 = 2;
    const VERDICT_PARTIALLY_TRUE: u8 = 3;
    const CLAIM_TYPE_BREAKING_NEWS: u8 = 2;
    const CLAIM_TYPE_TIMELESS: u8 = 0;

    // ============================================
    // HELPER FUNCTIONS
    // ============================================

    fun setup_test(aptos_framework: &signer, admin: &signer) {
        // Initialize timestamp for testing
        timestamp::set_time_has_started_for_testing(aptos_framework);
        timestamp::update_global_time_for_test_secs(1000000);
        
        // Create admin account
        account::create_account_for_test(@moveh);
        
        // Initialize the registry
        verdict_registry::initialize(admin);
    }

    // ============================================
    // TEST: Initialize Registry
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_initialize(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        // Verify total verdicts is 0
        let total = verdict_registry::get_total_verdicts();
        assert!(total == 0, 1);
    }

    // ============================================
    // TEST: Submit Verdict
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_submit_verdict(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        let claim_hash = string::utf8(b"abc123hash");
        let claim_signature = string::utf8(b"sig456");
        let keywords = vector::empty<string::String>();
        vector::push_back(&mut keywords, string::utf8(b"tesla"));
        vector::push_back(&mut keywords, string::utf8(b"elon"));
        let shelby_cid = string::utf8(b"QmXyz123");
        
        // Submit verdict
        verdict_registry::submit_verdict(
            admin,
            claim_hash,
            claim_signature,
            keywords,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_TRUE,
            85, // confidence
            shelby_cid,
            1000000 + 604800, // expires in 7 days
        );
        
        // Verify verdict exists
        assert!(verdict_registry::verdict_exists(string::utf8(b"abc123hash")), 2);
        
        // Verify total verdicts increased
        let total = verdict_registry::get_total_verdicts();
        assert!(total == 1, 3);
    }

    // ============================================
    // TEST: Get Verdict
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_get_verdict(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        let claim_hash = string::utf8(b"test_claim_hash");
        let claim_signature = string::utf8(b"test_sig");
        let keywords = vector::empty<string::String>();
        vector::push_back(&mut keywords, string::utf8(b"bitcoin"));
        let shelby_cid = string::utf8(b"QmTestCid");
        
        // Submit verdict
        verdict_registry::submit_verdict(
            admin,
            claim_hash,
            claim_signature,
            keywords,
            CLAIM_TYPE_TIMELESS,
            VERDICT_FALSE,
            92, // confidence
            shelby_cid,
            0, // never expires (timeless)
        );
        
        // Get verdict and verify
        let (verdict, confidence, cid, _timestamp, expiry, is_fresh) = 
            verdict_registry::get_verdict(string::utf8(b"test_claim_hash"));
        
        assert!(verdict == VERDICT_FALSE, 4);
        assert!(confidence == 92, 5);
        assert!(cid == string::utf8(b"QmTestCid"), 6);
        assert!(expiry == 0, 7); // never expires
        assert!(is_fresh == true, 8);
    }

    // ============================================
    // TEST: Keyword Search
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_keyword_search(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        // Submit first verdict with "crypto" keyword
        let keywords1 = vector::empty<string::String>();
        vector::push_back(&mut keywords1, string::utf8(b"crypto"));
        vector::push_back(&mut keywords1, string::utf8(b"bitcoin"));
        
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"hash1"),
            string::utf8(b"sig1"),
            keywords1,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_TRUE,
            90,
            string::utf8(b"cid1"),
            1000000 + 604800,
        );
        
        // Submit second verdict with "crypto" keyword
        let keywords2 = vector::empty<string::String>();
        vector::push_back(&mut keywords2, string::utf8(b"crypto"));
        vector::push_back(&mut keywords2, string::utf8(b"ethereum"));
        
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"hash2"),
            string::utf8(b"sig2"),
            keywords2,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_FALSE,
            85,
            string::utf8(b"cid2"),
            1000000 + 604800,
        );
        
        // Search by "crypto" keyword - should return 2 hashes
        let hashes = verdict_registry::get_hashes_by_keyword(string::utf8(b"crypto"));
        assert!(vector::length(&hashes) == 2, 9);
        
        // Search by "bitcoin" keyword - should return 1 hash
        let bitcoin_hashes = verdict_registry::get_hashes_by_keyword(string::utf8(b"bitcoin"));
        assert!(vector::length(&bitcoin_hashes) == 1, 10);
        
        // Search by non-existent keyword - should return 0
        let empty_hashes = verdict_registry::get_hashes_by_keyword(string::utf8(b"nonexistent"));
        assert!(vector::length(&empty_hashes) == 0, 11);
    }

    // ============================================
    // TEST: Verdict Freshness
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_verdict_freshness(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        // Submit verdict that expires in the future
        let keywords = vector::empty<string::String>();
        vector::push_back(&mut keywords, string::utf8(b"test"));
        
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"fresh_hash"),
            string::utf8(b"fresh_sig"),
            keywords,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_TRUE,
            80,
            string::utf8(b"fresh_cid"),
            2000000, // expires at 2000000 (current is 1000000)
        );
        
        // Should be fresh
        assert!(verdict_registry::is_verdict_fresh(string::utf8(b"fresh_hash")) == true, 12);
        
        // Submit verdict that never expires (timeless)
        let keywords2 = vector::empty<string::String>();
        vector::push_back(&mut keywords2, string::utf8(b"timeless"));
        
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"timeless_hash"),
            string::utf8(b"timeless_sig"),
            keywords2,
            CLAIM_TYPE_TIMELESS,
            VERDICT_TRUE,
            95,
            string::utf8(b"timeless_cid"),
            0, // 0 = never expires
        );
        
        // Timeless should always be fresh
        assert!(verdict_registry::is_verdict_fresh(string::utf8(b"timeless_hash")) == true, 13);
    }

    // ============================================
    // TEST: Duplicate Verdict Prevention
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    #[expected_failure(abort_code = 1, location = moveh::verdict_registry)]
    fun test_duplicate_verdict_fails(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        let keywords = vector::empty<string::String>();
        vector::push_back(&mut keywords, string::utf8(b"test"));
        
        // Submit first verdict
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"duplicate_hash"),
            string::utf8(b"sig1"),
            keywords,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_TRUE,
            80,
            string::utf8(b"cid1"),
            2000000,
        );
        
        // Try to submit duplicate - should fail
        let keywords2 = vector::empty<string::String>();
        vector::push_back(&mut keywords2, string::utf8(b"test2"));
        
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"duplicate_hash"), // same hash!
            string::utf8(b"sig2"),
            keywords2,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_FALSE,
            90,
            string::utf8(b"cid2"),
            2000000,
        );
    }

    // ============================================
    // TEST: Invalid Verdict Value
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    #[expected_failure(abort_code = 5, location = moveh::verdict_registry)]
    fun test_invalid_verdict_value(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        let keywords = vector::empty<string::String>();
        vector::push_back(&mut keywords, string::utf8(b"test"));
        
        // Try to submit with invalid verdict value (99)
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"invalid_hash"),
            string::utf8(b"sig"),
            keywords,
            CLAIM_TYPE_BREAKING_NEWS,
            99, // Invalid verdict value!
            80,
            string::utf8(b"cid"),
            2000000,
        );
    }

    // ============================================
    // TEST: Update Verdict (Admin Only)
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_update_verdict(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        let keywords = vector::empty<string::String>();
        vector::push_back(&mut keywords, string::utf8(b"update_test"));
        
        // Submit initial verdict
        verdict_registry::submit_verdict(
            admin,
            string::utf8(b"update_hash"),
            string::utf8(b"sig"),
            keywords,
            CLAIM_TYPE_BREAKING_NEWS,
            VERDICT_TRUE,
            70,
            string::utf8(b"old_cid"),
            2000000,
        );
        
        // Update the verdict
        verdict_registry::update_verdict(
            admin,
            string::utf8(b"update_hash"),
            VERDICT_PARTIALLY_TRUE,
            85,
            string::utf8(b"new_cid"),
        );
        
        // Verify update
        let (verdict, confidence, cid, _timestamp, _expiry, _is_fresh) = 
            verdict_registry::get_verdict(string::utf8(b"update_hash"));
        
        assert!(verdict == VERDICT_PARTIALLY_TRUE, 14);
        assert!(confidence == 85, 15);
        assert!(cid == string::utf8(b"new_cid"), 16);
    }

    // ============================================
    // TEST: Non-Existent Verdict
    // ============================================

    #[test(aptos_framework = @0x1, admin = @moveh)]
    fun test_verdict_not_exists(aptos_framework: &signer, admin: &signer) {
        setup_test(aptos_framework, admin);
        
        // Check non-existent verdict
        let exists = verdict_registry::verdict_exists(string::utf8(b"nonexistent_hash"));
        assert!(exists == false, 17);
    }
}
