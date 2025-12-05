# MoveH Backend

## Overview
This is the backend API for MoveH, an AI-powered fact-checking and blockchain verification system. It orchestrates agent workflows, generates PDF reports, and stores verdicts on the Aptos blockchain.

## Features
- FastAPI-based REST API
- Multi-agent fact-checking pipeline
- PDF report generation
- Shelby Protocol integration for decentralized storage
- Aptos blockchain smart contract interaction

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/MeghVyas3132/Aletheia.git

cd Aletheia/backend
```

### 2. Python Environment
Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
Or, if using Poetry:
```bash
poetry install
```

### 4. Environment Variables

**IMPORTANT**: Never commit secrets to version control!

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Then edit `.env` with your actual API keys:

```env
# AI & LLM APIs
GOOGLE_API_KEY=your_actual_gemini_api_key
TAVILY_API_KEY=your_actual_tavily_api_key

# Blockchain Configuration
APTOS_PRIVATE_KEY=0x_your_actual_private_key
APTOS_MODULE_ADDRESS=0x_your_deployed_contract_address
GEOMI_API_KEY=your_actual_geomi_api_key  # Optional
```

**How to get these keys:**

- **GOOGLE_API_KEY**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **TAVILY_API_KEY**: Sign up at [Tavily](https://tavily.com/)
- **APTOS_PRIVATE_KEY**: Generate with `aptos account create` or use the Aptos SDK
- **APTOS_MODULE_ADDRESS**: Your deployed VerdictRegistry contract address
- **GEOMI_API_KEY**: Optional, get from [Geomi](https://geomi.dev/) for higher rate limits

⚠️ **Security Notes:**
- The `.env` file is already in `.gitignore` - never remove it from there
- Never hardcode keys in source code
- Never commit the `.aptos/config.yaml` file (already gitignored)
- For CI/CD, use GitHub Secrets or similar secret management tools

### 5. Run the API Server
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test the API
Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

## Key Files
- `api.py` — Main FastAPI app
- `agents/` — Agent logic (FactChecker, ForensicExpert, TheJudge, Shelby)
- `blockchain/` — Aptos blockchain client and contract logic
- `storage/` — PDF reports and temporary files

## Useful Commands
- Run all tests:
  ```bash
  python -m unittest discover
  ```
- Format code:
  ```bash
  black .
  ```

## Troubleshooting
- Ensure all API keys are valid and set in `.env`
- For blockchain errors, check your Aptos private key and contract deployment
- For Shelby uploads, ensure the CLI is installed and configured

## License
MIT

---
For more details, see the main project [README](../README.md).
