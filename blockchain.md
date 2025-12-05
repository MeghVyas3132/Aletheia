## What's Stored on Blockchain (Aptos)

The **VerdictRegistry** smart contract stores the following data for each fact-checked claim:

| Field | Type | Description |
|-------|------|-------------|
| `claim_hash` | String | SHA-256 hash of the normalized claim text |
| `claim_signature` | String | Semantic signature for fuzzy matching of similar claims |
| `keywords` | vector<String> | Extracted keywords for search/discovery |
| `claim_type` | u8 | Type: 0=Timeless, 1=Historical, 2=Breaking News, 3=Ongoing, 4=Prediction, 5=Status |
| `verdict` | u8 | **1**=TRUE, **2**=FALSE, **3**=PARTIALLY_TRUE, **4**=UNVERIFIABLE |
| `confidence` | u8 | Confidence score (0-100%) |
| `shelby_cid` | String | **Shelby Protocol CID** pointing to the full PDF report |
| `timestamp` | u64 | Unix timestamp when verdict was submitted |
| `expiry` | u64 | When verdict expires (0 = never) |
| `submitter` | address | Wallet address that submitted the verdict |

### Key Design Points:

1. **Deduplication** - Before running expensive AI agents, the system checks if a verdict already exists via `claim_hash`

2. **Off-chain Data** - The full PDF report is stored on **Shelby Protocol** (decentralized storage), only the CID reference is stored on-chain

3. **Searchability** - Keywords are indexed for discovery

4. **Expiration** - Verdicts can expire (useful for time-sensitive claims like "breaking news")