# Move Smart Contract: Verdict Registry
### 📍 Deployed Contract Info
| Field | Value |
|-------|-------|
| **Network** | Aptos Testnet |
| **Contract Address** | `0xba58879f1b139282d87882e084a7f76a43e65e142ddd6037fbc7c5157798fafe` |
| **Module Name** | `verdict_registry` |
| **Explorer** | [View on Aptos Explorer](https://explorer.aptoslabs.com/account/0xba58879f1b139282d87882e084a7f76a43e65e142ddd6037fbc7c5157798fafe/modules?network=testnet) |

---

### 📦 What We Store On-Chain

#### **VerdictRecord** (per fact-checked claim)
| Field | Type | Description |
|-------|------|-------------|
| `claim_hash` | String | SHA-256 hash of normalized claim text (unique ID) |
| `claim_signature` | String | Semantic signature for fuzzy matching |
| `keywords` | vector<String> | Keywords extracted for search |
| `claim_type` | u8 | 0=Timeless, 1=Historical, 2=Breaking, 3=Ongoing, 4=Prediction, 5=Status |
| `verdict` | u8 | 1=TRUE, 2=FALSE, 3=PARTIALLY_TRUE, 4=UNVERIFIABLE |
| `confidence` | u8 | 0-100 confidence score |
| `shelby_cid` | String | IPFS CID where full report is stored (via Shelby) |
| `timestamp` | u64 | Unix timestamp when submitted |
| `expiry` | u64 | When verdict expires (0 = never) |
| `submitter` | address | Who submitted the verdict |

#### **VerdictRegistry** (global state)
| Field | Type | Description |
|-------|------|-------------|
| `verdicts` | Table<String, VerdictRecord> | Main storage: claim_hash → verdict |
| `total_verdicts` | u64 | Counter of all verdicts |
| `admin` | address | Admin who can update verdicts |

#### **KeywordIndex** (for search)
| Field | Type | Description |
|-------|------|-------------|
| `index` | Table<String, vector<String>> | keyword → list of claim_hashes |

---

### 🔧 Contract Functions

#### Entry Functions (write to blockchain)
| Function | Description |
|----------|-------------|
| `initialize()` | Creates the registry (called once) ✅ Done |
| `submit_verdict(...)` | Submit a new fact-check verdict |
| `update_verdict(...)` | Admin can update existing verdict |

#### View Functions (read from blockchain)
| Function | Returns | Description |
|----------|---------|-------------|
| `verdict_exists(claim_hash)` | bool | Check if claim was already fact-checked |
| `get_verdict(claim_hash)` | (verdict, confidence, cid, timestamp, expiry, is_fresh) | Get verdict details |
| `get_hashes_by_keyword(keyword)` | vector<String> | Search by keyword |
| `get_total_verdicts()` | u64 | Total verdicts count |
| `is_verdict_fresh(claim_hash)` | bool | Check if verdict hasn't expired |

---

### 🔄 Flow: How It Works

```
User submits claim → Python agents fact-check it
                            ↓
              Full report uploaded to Shelby (IPFS)
                            ↓
              Verdict summary submitted to Aptos:
              - claim_hash (for deduplication)
              - verdict (TRUE/FALSE/etc)
              - confidence score
              - shelby_cid (link to full report)
              - keywords (for search)
              - expiry (based on claim type)
                            ↓
              On-chain: Immutable, transparent, searchable
```

---

### 🎯 Purpose

1. **Deduplication** - Before fact-checking, check if `verdict_exists(claim_hash)` 
2. **Transparency** - All verdicts are public and verifiable
3. **Search** - Find related claims by keyword
4. **Freshness** - Breaking news verdicts expire, timeless facts don't
5. **Audit Trail** - Full reports stored on IPFS via Shelby

---

### ✅ Tests (9/9 Passing)
- `test_initialize`
- `test_submit_verdict`
- `test_get_verdict`
- `test_keyword_search`
- `test_verdict_freshness`
- `test_duplicate_verdict_fails`
- `test_invalid_verdict_value`
- `test_update_verdict`
- `test_verdict_not_exists`

---

Ready to build the **Python Aptos client** (`blockchain/aptos_client.py`) to connect your main.py to this contract? 🚀