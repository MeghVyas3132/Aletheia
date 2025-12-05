/// MoveH Verdict Registry
/// Stores fact-check verdicts on-chain for transparency and deduplication
module moveh::verdict_registry {
    use std::string::String;
    use std::vector;
    use std::signer;
    use aptos_framework::timestamp;
    use aptos_framework::event;
    use aptos_framework::table::{Self, Table};

    // ============================================
    // ERRORS
    // ============================================
    
    /// Verdict already exists for this claim hash
    const E_VERDICT_EXISTS: u64 = 1;
    /// Verdict not found
    const E_VERDICT_NOT_FOUND: u64 = 2;
    /// Registry not initialized
    const E_NOT_INITIALIZED: u64 = 3;
    /// Unauthorized operation
    const E_UNAUTHORIZED: u64 = 4;
    /// Invalid verdict value
    const E_INVALID_VERDICT: u64 = 5;

    // ============================================
    // CLAIM TYPES (matching Python ClaimType enum)
    // ============================================
    
    const CLAIM_TYPE_TIMELESS: u8 = 0;
    const CLAIM_TYPE_HISTORICAL: u8 = 1;
    const CLAIM_TYPE_BREAKING_NEWS: u8 = 2;
    const CLAIM_TYPE_ONGOING: u8 = 3;
    const CLAIM_TYPE_PREDICTION: u8 = 4;
    const CLAIM_TYPE_STATUS: u8 = 5;

    // ============================================
    // VERDICT VALUES
    // ============================================
    
    const VERDICT_TRUE: u8 = 1;
    const VERDICT_FALSE: u8 = 2;
    const VERDICT_PARTIALLY_TRUE: u8 = 3;
    const VERDICT_UNVERIFIABLE: u8 = 4;

    // ============================================
    // STRUCTS
    // ============================================

    /// A single verdict record stored on-chain
    struct VerdictRecord has store, copy, drop {
        /// SHA-256 hash of normalized claim text
        claim_hash: String,
        /// Semantic signature for fuzzy matching
        claim_signature: String,
        /// Keywords extracted from claim (for search)
        keywords: vector<String>,
        /// Claim type (0-5)
        claim_type: u8,
        /// Verdict: 1=TRUE, 2=FALSE, 3=PARTIALLY_TRUE, 4=UNVERIFIABLE
        verdict: u8,
        /// Confidence score (0-100)
        confidence: u8,
        /// Shelby CID where full report is stored
        shelby_cid: String,
        /// Unix timestamp when verdict was submitted
        timestamp: u64,
        /// Unix timestamp when verdict expires (0 = never)
        expiry: u64,
        /// Address that submitted this verdict
        submitter: address,
    }

    /// Main registry holding all verdicts
    struct VerdictRegistry has key {
        /// Map from claim_hash to VerdictRecord
        verdicts: Table<String, VerdictRecord>,
        /// Total number of verdicts stored
        total_verdicts: u64,
        /// Registry owner/admin
        admin: address,
    }

    /// Index for keyword-based search
    struct KeywordIndex has key {
        /// Map from keyword to list of claim hashes
        index: Table<String, vector<String>>,
    }

    // ============================================
    // EVENTS
    // ============================================

    #[event]
    struct VerdictSubmitted has drop, store {
        claim_hash: String,
        verdict: u8,
        confidence: u8,
        shelby_cid: String,
        timestamp: u64,
        submitter: address,
    }

    // ============================================
    // INITIALIZATION
    // ============================================

    /// Initialize the verdict registry (called once by deployer)
    public entry fun initialize(account: &signer) {
        let addr = signer::address_of(account);
        
        // Create main registry
        move_to(account, VerdictRegistry {
            verdicts: table::new(),
            total_verdicts: 0,
            admin: addr,
        });

        // Create keyword index
        move_to(account, KeywordIndex {
            index: table::new(),
        });
    }

    // ============================================
    // CORE FUNCTIONS
    // ============================================

    /// Submit a new verdict to the registry
    public entry fun submit_verdict(
        account: &signer,
        claim_hash: String,
        claim_signature: String,
        keywords: vector<String>,
        claim_type: u8,
        verdict: u8,
        confidence: u8,
        shelby_cid: String,
        expiry: u64,
    ) acquires VerdictRegistry, KeywordIndex {
        let submitter = signer::address_of(account);
        let registry_addr = @moveh;
        
        // Ensure registry exists
        assert!(exists<VerdictRegistry>(registry_addr), E_NOT_INITIALIZED);
        
        // Validate verdict value
        assert!(verdict >= VERDICT_TRUE && verdict <= VERDICT_UNVERIFIABLE, E_INVALID_VERDICT);
        
        let registry = borrow_global_mut<VerdictRegistry>(registry_addr);
        
        // Check if verdict already exists
        assert!(!table::contains(&registry.verdicts, claim_hash), E_VERDICT_EXISTS);
        
        let now = timestamp::now_seconds();
        
        // Create verdict record
        let record = VerdictRecord {
            claim_hash,
            claim_signature,
            keywords,
            claim_type,
            verdict,
            confidence,
            shelby_cid,
            timestamp: now,
            expiry,
            submitter,
        };
        
        // Store in main table
        table::add(&mut registry.verdicts, claim_hash, record);
        registry.total_verdicts = registry.total_verdicts + 1;
        
        // Index keywords
        let keyword_index = borrow_global_mut<KeywordIndex>(registry_addr);
        let i = 0;
        let len = vector::length(&keywords);
        while (i < len) {
            let keyword = *vector::borrow(&keywords, i);
            if (table::contains(&keyword_index.index, keyword)) {
                let hashes = table::borrow_mut(&mut keyword_index.index, keyword);
                vector::push_back(hashes, claim_hash);
            } else {
                let new_vec = vector::empty<String>();
                vector::push_back(&mut new_vec, claim_hash);
                table::add(&mut keyword_index.index, keyword, new_vec);
            };
            i = i + 1;
        };
        
        // Emit event
        event::emit(VerdictSubmitted {
            claim_hash,
            verdict,
            confidence,
            shelby_cid,
            timestamp: now,
            submitter,
        });
    }

    // ============================================
    // VIEW FUNCTIONS
    // ============================================

    // Check if a verdict exists for the given claim hash
    #[view]
    public fun verdict_exists(claim_hash: String): bool acquires VerdictRegistry {
        let registry_addr = @moveh;
        if (!exists<VerdictRegistry>(registry_addr)) {
            return false
        };
        let registry = borrow_global<VerdictRegistry>(registry_addr);
        table::contains(&registry.verdicts, claim_hash)
    }

    // Get verdict details by claim hash
    #[view]
    public fun get_verdict(claim_hash: String): (u8, u8, String, u64, u64, bool) acquires VerdictRegistry {
        let registry_addr = @moveh;
        assert!(exists<VerdictRegistry>(registry_addr), E_NOT_INITIALIZED);
        
        let registry = borrow_global<VerdictRegistry>(registry_addr);
        assert!(table::contains(&registry.verdicts, claim_hash), E_VERDICT_NOT_FOUND);
        
        let record = table::borrow(&registry.verdicts, claim_hash);
        let now = timestamp::now_seconds();
        let is_fresh = record.expiry == 0 || record.expiry > now;
        
        (record.verdict, record.confidence, record.shelby_cid, record.timestamp, record.expiry, is_fresh)
    }

    // Get claim hashes for a keyword
    #[view]
    public fun get_hashes_by_keyword(keyword: String): vector<String> acquires KeywordIndex {
        let registry_addr = @moveh;
        if (!exists<KeywordIndex>(registry_addr)) {
            return vector::empty<String>()
        };
        
        let keyword_index = borrow_global<KeywordIndex>(registry_addr);
        if (table::contains(&keyword_index.index, keyword)) {
            *table::borrow(&keyword_index.index, keyword)
        } else {
            vector::empty<String>()
        }
    }

    // Get total verdicts count
    #[view]
    public fun get_total_verdicts(): u64 acquires VerdictRegistry {
        let registry_addr = @moveh;
        if (!exists<VerdictRegistry>(registry_addr)) {
            return 0
        };
        let registry = borrow_global<VerdictRegistry>(registry_addr);
        registry.total_verdicts
    }

    // Check if verdict is still fresh (not expired)
    #[view]
    public fun is_verdict_fresh(claim_hash: String): bool acquires VerdictRegistry {
        let registry_addr = @moveh;
        assert!(exists<VerdictRegistry>(registry_addr), E_NOT_INITIALIZED);
        
        let registry = borrow_global<VerdictRegistry>(registry_addr);
        if (!table::contains(&registry.verdicts, claim_hash)) {
            return false
        };
        
        let record = table::borrow(&registry.verdicts, claim_hash);
        let now = timestamp::now_seconds();
        
        // Expiry of 0 means never expires
        record.expiry == 0 || record.expiry > now
    }

    // ============================================
    // ADMIN FUNCTIONS
    // ============================================

    /// Update verdict (admin only, for corrections)
    public entry fun update_verdict(
        account: &signer,
        claim_hash: String,
        new_verdict: u8,
        new_confidence: u8,
        new_shelby_cid: String,
    ) acquires VerdictRegistry {
        let caller = signer::address_of(account);
        let registry_addr = @moveh;
        
        assert!(exists<VerdictRegistry>(registry_addr), E_NOT_INITIALIZED);
        
        let registry = borrow_global_mut<VerdictRegistry>(registry_addr);
        assert!(caller == registry.admin, E_UNAUTHORIZED);
        assert!(table::contains(&registry.verdicts, claim_hash), E_VERDICT_NOT_FOUND);
        assert!(new_verdict >= VERDICT_TRUE && new_verdict <= VERDICT_UNVERIFIABLE, E_INVALID_VERDICT);
        
        let record = table::borrow_mut(&mut registry.verdicts, claim_hash);
        record.verdict = new_verdict;
        record.confidence = new_confidence;
        record.shelby_cid = new_shelby_cid;
        record.timestamp = timestamp::now_seconds();
    }
}
