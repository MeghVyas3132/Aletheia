# Aletheia

**AI-Powered Fact-Checking with Blockchain Verification**

Aletheia is a multi-agent fact-checking system that verifies claims using AI and stores immutable verdicts on the Aptos blockchain. The system combines web search, forensic text analysis, and trust-weighted consensus to produce probabilistic verdicts with full transparency.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [API Reference](#api-reference)
8. [Blockchain Integration](#blockchain-integration)
9. [Smart Contract](#smart-contract)
10. [Security](#security)
11. [Known Limitations](#known-limitations)
12. [Contributing](#contributing)
13. [License](#license)

---

## Overview

### Problem Statement

Misinformation spreads significantly faster than factual content. Manual fact-checking is slow and resource-intensive, automated filters are easily circumvented, and AI-generated verdicts lack accountability and transparency.

### Solution

Aletheia provides a security checkpoint for information verification:

- **Multi-Agent AI System**: Three specialized agents work in parallel to analyze claims from different perspectives
- **Probabilistic Verdicts**: Results are expressed as confidence percentages with detailed reasoning
- **Blockchain Immutability**: All verdicts are permanently recorded on the Aptos blockchain
- **Decentralized Evidence Storage**: Full PDF reports are stored on Shelby Protocol with on-chain references

---

## Architecture

```
aletheia/
├── backend/
│   ├── agents/
│   │   ├── fact_checker.py      # Agent 1: Web search and evidence gathering
│   │   ├── forensic_expert.py   # Agent 2: Linguistic and AI detection analysis
│   │   ├── judge.py             # Agent 3: Trust-weighted verdict synthesis
│   │   ├── claim_processor.py   # Claim classification and metadata extraction
│   │   └── shelby.py            # PDF generation and decentralized storage
│   ├── blockchain/
│   │   ├── aptos_client.py      # Aptos blockchain interaction
│   │   └── chain_lookup.py      # On-chain verdict lookup and deduplication
│   ├── move_smart_contract/
│   │   └── sources/
│   │       └── verdict_registry.move   # Move smart contract
│   ├── api.py                   # FastAPI application
│   └── main.py                  # CLI interface
└── frontend/
    ├── app/                     # Next.js application
    └── components/              # React components
```

### Processing Pipeline

```
User submits claim
        |
        v
+-----------------------------------+
|  Deduplication Check              |
|  Query blockchain for existing    |
|  verdict via claim hash           |
+-----------------------------------+
        |
        +-- Existing verdict found --> Return cached result
        |
        v No existing verdict
+-----------------------------------+
|  Parallel Agent Execution         |
|                                   |
|  +-------------+ +-------------+  |
|  | Fact Checker| |  Forensic   |  |
|  |   Agent 1   | |   Agent 2   |  |
|  +------+------+ +------+------+  |
|         |               |         |
|         +-------+-------+         |
|                 v                 |
|         +-------------+           |
|         |  The Judge  |           |
|         |   Agent 3   |           |
|         +-------------+           |
+-----------------------------------+
        |
        v
+-----------------------------------+
|  Output Generation                |
|  - Generate PDF report            |
|  - Upload to Shelby Protocol      |
|  - Submit verdict to Aptos        |
+-----------------------------------+
        |
        v
    Return verdict with confidence score
```

### Agent Descriptions

**Agent 1: Fact Checker**
- Generates targeted search queries based on the claim
- Executes parallel web searches using Tavily API
- Gathers evidence from authoritative sources (news outlets, official sites, regulatory filings)
- Iterates if initial evidence is insufficient
- Outputs preliminary verdict with supporting evidence

**Agent 2: Forensic Expert**
- Analyzes linguistic patterns for manipulation indicators
- Detects urgency and panic markers
- Evaluates grammar quality and writing professionalism
- Checks for AI-generated content signatures
- Outputs integrity score with penalty breakdown

**Agent 3: The Judge**
- Normalizes inputs from both agents into comparable metrics
- Applies dynamic trust-weighted consensus based on evidence quality
- Generates final probabilistic verdict
- Produces detailed reasoning and audit evidence package

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Orchestration | LangGraph | Multi-agent state machine workflows |
| Language Model | Gemini 2.5 Flash | Fast inference for all agent reasoning |
| Web Search | Tavily API | Real-time evidence gathering |
| Backend API | FastAPI | REST API with async support |
| Frontend | Next.js, TypeScript | User interface |
| PDF Generation | ReportLab | Professional report creation |
| Blockchain | Aptos (Move) | Immutable verdict storage |
| Decentralized Storage | Shelby Protocol | Evidence preservation |

---

## Installation

### Prerequisites

- Python 3.12 or higher
- Node.js 18 or higher
- uv or pip (Python package manager)
- Aptos CLI (optional, for smart contract deployment)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/MeghVyas3132/Aletheia.git
cd Aletheia/backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
# Or using uv:
uv pip install -e .

# Copy environment template
cp .env.example .env
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
# Or using pnpm:
pnpm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

---

## Configuration

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Required: AI and Search APIs
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key

# Required: Blockchain Configuration
APTOS_PRIVATE_KEY=0x_your_private_key
APTOS_MODULE_ADDRESS=0x_your_deployed_contract_address

# Optional: Enhanced Rate Limits
GEOMI_API_KEY=your_geomi_api_key
```

### Obtaining API Keys

| Key | Source |
|-----|--------|
| GOOGLE_API_KEY | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| TAVILY_API_KEY | [Tavily](https://tavily.com/) |
| APTOS_PRIVATE_KEY | Generate using `aptos account create` |
| GEOMI_API_KEY | [Geomi](https://geomi.dev/) (optional) |

---

## Usage

### Command Line Interface

```bash
cd backend
source .venv/bin/activate
python main.py
```

### API Server

```bash
cd backend
source .venv/bin/activate
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API documentation at `http://localhost:8000/docs`

### Frontend Application

```bash
cd frontend
npm run dev
```

Access the web interface at `http://localhost:3000`

---

## API Reference

### POST /verify

Submit a claim for verification.

**Request Body:**
```json
{
  "claim": "The claim text to verify"
}
```

**Response:**
```json
{
  "verdict": "TRUE | FALSE | PROBABLY_TRUE | PROBABLY_FALSE | UNCERTAIN",
  "confidence": 85,
  "reasoning": "Detailed explanation of the verdict",
  "sources": ["list", "of", "sources"],
  "transaction_hash": "0x...",
  "pdf_url": "https://shelby.protocol/cid/..."
}
```

### GET /lookup/{claim_hash}

Check if a verdict already exists for a claim.

**Response:**
```json
{
  "exists": true,
  "verdict": "TRUE",
  "confidence": 92,
  "timestamp": 1701878400,
  "shelby_cid": "Qm..."
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "online",
  "service": "Aletheia API"
}
```

---

## Blockchain Integration

### Network Configuration

- **Network**: Aptos Testnet
- **Explorer**: [Aptos Explorer](https://explorer.aptoslabs.com/?network=testnet)

### On-Chain Data Structure

Each verdict stored on-chain contains:

| Field | Type | Description |
|-------|------|-------------|
| claim_hash | String | SHA-256 hash of normalized claim text |
| claim_signature | String | Semantic signature for similarity matching |
| keywords | vector | Extracted keywords for discoverability |
| claim_type | u8 | Classification (0=Timeless, 1=Historical, 2=Breaking, 3=Ongoing, 4=Prediction, 5=Status) |
| verdict | u8 | Result (1=TRUE, 2=FALSE, 3=PARTIALLY_TRUE, 4=UNVERIFIABLE) |
| confidence | u8 | Confidence percentage (0-100) |
| shelby_cid | String | Reference to full PDF report on Shelby Protocol |
| timestamp | u64 | Unix timestamp of submission |
| expiry | u64 | Expiration timestamp (0 for permanent) |
| submitter | address | Wallet address of submitter |

### Design Principles

1. **Deduplication**: Claims are checked against existing verdicts before processing to reduce costs
2. **Off-Chain Storage**: Full reports are stored on Shelby Protocol; only the CID is stored on-chain
3. **Expiration Support**: Time-sensitive claims can have expiration timestamps
4. **Searchability**: Keywords enable verdict discovery

---

## Smart Contract

The VerdictRegistry smart contract is located at `backend/move_smart_contract/sources/verdict_registry.move`.

### Deployment

```bash
cd backend/move_smart_contract

# Compile the contract
aptos move compile

# Deploy to testnet
aptos move publish --profile testnet
```

### Key Functions

- `initialize()`: Set up the registry (called once)
- `submit_verdict()`: Store a new verdict on-chain
- `get_verdict()`: Retrieve an existing verdict by claim hash
- `verdict_exists()`: Check if a verdict exists for a claim

---

## Security

### Environment Variables

- Store all secrets in `.env` files (already in `.gitignore`)
- Never commit API keys, private keys, or credentials
- Use `.env.example` as a template without real values
- For production, use secret management services (AWS Secrets Manager, HashiCorp Vault)

### Private Key Management

- Generate keys using `aptos account create`
- Store private keys only in environment variables
- Never commit `.aptos/config.yaml`
- Rotate keys periodically
- Consider hardware wallets for production deployments

### Input Validation

- All claim inputs are sanitized before processing
- Prompt injection patterns are filtered
- Rate limiting is implemented on API endpoints

### Reporting Vulnerabilities

Report security vulnerabilities privately via GitHub Security tab. Do not open public issues for security concerns.

---

## Known Limitations

### Search and Evidence

- **Breaking News**: Very recent events may not be indexed; returns "TOO_EARLY_TO_VERIFY"
- **Paywalled Content**: Limited access to premium news sources
- **Language Support**: Optimized for English; other languages may have reduced accuracy
- **Niche Topics**: Specialized claims may lack mainstream source coverage

### Analysis

- **Sophisticated Misinformation**: Well-written false content may receive higher integrity scores
- **AI Detection**: Advanced AI-generated text may evade detection
- **Context Sensitivity**: Domain-specific terminology may be misinterpreted

### Blockchain

- **Semantic Duplicates**: Rephrased claims generate different hashes
- **Cache Staleness**: Expired verdicts require re-verification
- **Transaction Costs**: Requires funded wallet for on-chain submissions

### Claim Types Not Supported

- Predictions and future claims
- Subjective opinions
- Satirical content (may be incorrectly flagged)
- Image or video verification

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style and conventions
- Add tests for new functionality
- Update documentation for API changes
- Never commit secrets or credentials

---

## License

MIT License

---

## Acknowledgments

Built for the Aptos Hackathon. Aletheia uses the Aptos blockchain for immutable verdict storage and Shelby Protocol for decentralized evidence preservation.

---

*Aletheia - Trust, but Verify*
