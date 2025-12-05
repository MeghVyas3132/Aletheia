# 🛡️ MoveH - AI Fact-Checking on Blockchain

<div align="center">

![MoveH](https://img.shields.io/badge/MoveH-AI%20Fact%20Checker-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-purple?style=for-the-badge)
![Aptos](https://img.shields.io/badge/Aptos-Blockchain-cyan?style=for-the-badge)

**Multi-Agent Verification System with Blockchain-Stamped Verdicts**

[Features](#features) • [Architecture](#architecture) • [Setup](#setup) • [Usage](#usage) • [Workflows](#workflows)

</div>

---

## 🚩 Problem

Misinformation spreads **6x faster** than truth. Manual fact-checking is slow, filters are easily gamed, and AI verdicts lack accountability.

---

## 💡 Solution

MoveH is a **security checkpoint** for information:
- **Multi-Agent AI**: Three specialized agents
- **Probability Verdicts**: e.g. "78% likely FALSE" with reasoning
- **Blockchain Proof**: Immutable verdicts on Aptos/Shelby

---

## ✨ Features

- 🔍 Fact Checker: Async web search
- 🕵️ Forensic Expert: Linguistic & AI detection
- ⚖️ The Judge: Trust-weighted consensus
- ⚡ Parallel execution
- 📄 PDF reports
- ☁️ Shelby decentralized storage
- ⛓️ Aptos blockchain smart contract
- 🔄 Deduplication (on-chain check before agents)

---

## 🏗️ Architecture

```
moveh/
├── backend/         # FastAPI, agents, blockchain, PDF
├── frontend/        # Next.js UI
├── move_smart_contract/  # Move contract
├── workflows/       # Mermaid diagrams
├── reports/         # PDF reports
├── logs/            # Execution logs
└── slides/          # Presentations
```

---

## 🛠️ Tech Stack

| Component         | Technology         | Purpose                        |
|-------------------|-------------------|--------------------------------|
| AI Orchestration  | LangGraph         | Multi-agent state machines     |
| LLM               | Gemini 2.5 Flash  | Fast, cost-effective inference |
| Web Search        | Tavily API        | Real-time fact verification    |
| PDF Generation    | ReportLab         | Professional reports           |
| Blockchain        | Aptos (Move)      | Immutable verdict storage      |
| Decentralized Storage | Shelby Protocol | Evidence preservation         |

---

## 📦 Setup

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- [uv](https://docs.astral.sh/uv/) or pip
- Shelby CLI (optional for decentralized storage)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MeghVyas3132/Aletheia.git
   cd Aletheia
   ```

2. **Set up environment variables:**
   ```bash
   # Copy the example env file
   cp .env.example .env
   
   # Edit .env with your actual API keys
   nano .env  # or use your preferred editor
   ```

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn api:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
pnpm dev
```

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Required
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
APTOS_PRIVATE_KEY=0x_your_private_key
APTOS_MODULE_ADDRESS=0x_your_contract_address

# Optional
GEOMI_API_KEY=your_geomi_api_key  # For higher Aptos rate limits
```

**🔐 Security Best Practices:**
- ✅ `.env` files are gitignored - never commit them
- ✅ Use `.env.example` as a template (no real secrets)
- ✅ For production/CI: use GitHub Secrets, AWS Secrets Manager, etc.
- ✅ Rotate keys regularly
- ❌ Never hardcode secrets in source code
- ❌ Never commit `.aptos/config.yaml` (contains private keys)

**Where to get API keys:**
- **GOOGLE_API_KEY**: [Google AI Studio](https://aistudio.google.com/app/apikey)
- **TAVILY_API_KEY**: [Tavily API](https://tavily.com/)
- **GEOMI_API_KEY**: [Geomi Dev](https://geomi.dev/) (optional)
- **APTOS_PRIVATE_KEY**: Generate with `aptos account create`

---

## 🚀 Usage

- **Interactive:** `python main.py`
- **API:** Visit [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend:** Visit [http://localhost:3000](http://localhost:3000)

---

## ⛓️ Blockchain

- **Network:** Aptos Testnet
- **Module:** `verdict_registry`
- **Contract Address:** Set in your `.env` as `APTOS_MODULE_ADDRESS`

View transactions on [Aptos Explorer](https://explorer.aptoslabs.com/?network=testnet)

---

## 🤝 Contributing

1. Fork and clone
2. Create a feature branch
3. Commit and push
4. Open a PR

---

## 📄 License

MIT License

---

<div align="center">

**🛡️ MoveH - "Trust, but Verify — On-Chain"**

Built with ❤️ for the Aptos Hackathon

</div>
