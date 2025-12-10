# Aletheia — AI Fact-Checking Platform

AI-powered, multi-agent fact-checking with optional on-chain verdict recording.

This repository contains the Aletheia system: a backend (FastAPI + LangGraph agents) and a Next.js frontend. Aletheia ingests a claim, runs a parallel multi-agent verification pipeline (search-based evidence gathering, forensic text analysis, and debate-style juried synthesis), and returns a probabilistic verdict along with audit evidence. Optionally, finalized verdicts can be recorded on the Aptos blockchain and referenced to immutable evidence stored via Shelby Protocol.

## Table of contents

- Overview
- Architecture & components
- Quickstart (local & Docker)
- Configuration & environment variables
- API reference (core endpoints)
- Developer notes (tests, agents, debugging)
- Deployment (Render, Docker)
- Security & operational considerations
- Contributing
- License


## Overview

Why Aletheia?

- Misinformation spreads quickly; manual fact-checking cannot scale.
- Aletheia combines evidence search, automated forensic checks, and a small juried consensus to produce transparent, explainable verdicts with confidence scores.

What it returns

- Verdict: TRUE / FALSE / UNCERTAIN (and probabilistic variants internally)
- Confidence: numeric percentage
- Reasoning: human-readable summary and supporting evidence
- Optional artifacts: PDF report (Shelby Protocol CID) and on-chain transaction hash (Aptos)


## Architecture & key components

Top-level layout

backend/  — FastAPI server, agent implementations, DOW (truth market) integration, scheduler, and utilities
frontend/ — Next.js app (TypeScript) for claim submission and results display
move_smart_contract/ — Move contract sources (verdict registry)

Important backend modules

- agents/ — Multi-agent implementations
  - fact_checker.py — builds search queries, fetches evidence (Tavily), and produces an evidence dossier
  - forensic_expert.py — linguistic analysis, AI-detection heuristics, integrity scoring
  - ai_council.py — structured adversarial debate and juried voting (Prosecutor/Defender/Jurors)
  - devils_advocate.py — adversarial counter-arguments to surface weaknesses
  - shelby.py — PDF generation and Shelby Protocol upload

  Note: The Aletheia system is composed of more than 10 specialized AI agents. In addition to the core agents listed above, the codebase includes multiple domain-specific agents, witness/auxiliary agents, and orchestration helpers. Example roles include domain-specific search agents, evidence extractors, the forensic expert, the fact checker, a Devil's Advocate, the Judge, and lightweight witness agents that surface supporting context from specialized sources.

- api_v2.py — primary HTTP endpoints (/verify, /verify_stream, /health, market endpoints)
- main.py — CLI tools and PDF/report helpers
- scheduler.py — background jobs (market resolution, challenge processing)
- verification_history.py — local verification DB with fallback paths
- blockchain/ — Aptos client wrappers and lookup helpers

DOW (Decentralized Oracle of Wisdom)

The system includes a Decentralized Oracle of Wisdom (DOW) component that implements a staking-based challenge mechanism. DOW uses SOL tokens as the primary incentive currency: users who doubt an Aletheia verdict can challenge it by staking SOL. The challenge is resolved by a community vote (the truth market / juried mechanism). If the community vote favors the challenger, the challenger is returned their stake and may receive additional rewards; if the vote upholds the original verdict, the challenger's stake is deducted (distributed according to the market rules). This design aligns financial incentives with accurate verification and allows users to dispute results transparently.


## Quickstart — Local (recommended for development)

1) Backend (Python)

- Create and activate a Python 3.12+ virtual environment

  python3 -m venv .venv
  source .venv/bin/activate

- Install Python dependencies

  # inside backend/
  pip install -r requirements.txt

- Create a backend `.env` (see Configuration below)

- Run the API in dev mode

  cd backend
  uvicorn api_v2:app --reload --host 0.0.0.0 --port 8000

The API docs are available at http://localhost:8000/docs


2) Frontend (Next.js)

  cd frontend
  npm install
  npm run dev

Open http://localhost:3000 and point the frontend to the backend using NEXT_PUBLIC_API_BASE_URL or the built-in env handling.


3) Docker & docker-compose (local reproducible run)

Use the provided Dockerfiles for backend and frontend. The backend Dockerfile reads PORT for Render compatibility.

  docker-compose up --build


## Configuration & environment variables

Create a `.env` file in `backend/` with at minimum the following keys:

- GROQ_API_KEY — Groq/Gemini LLM key (used by LLM provider)
- TAVILY_API_KEY — Tavily search API key
- APTOS_PRIVATE_KEY — Private key for Aptos transactions (only if submitting on-chain)
- APTOS_MODULE_ADDRESS — Address where verdict registry is deployed (optional)
- ADMIN_API_KEY — (optional) admin key used by protected endpoints

Note: Do not commit `.env` to source control. Use the `.env.example` template if present.


## API reference (core)

POST /verify

- Submits a claim for verification. The request body must contain { "claim": "..." }.
- Returns a JSON payload with verdict, confidence, reasoning, sources, and optional record references.

POST /verify_stream

- Streaming version of /verify that yields intermediate agent outputs, debate rounds, and vote tallies in real time.

GET /health

- Basic health check. See /health/detailed for a more comprehensive component status.

GET /lookup/{claim_hash}

- Checks for an existing on-chain or local cached verdict for the normalized claim.

See `backend/api_v2.py` for more endpoints (market/DOW operations and admin utilities).


## Developer notes

Tests

- There are a few integration and smoke tests under `backend/` such as `test_full_system.py` and `test_aptos.py`. Run them from the backend virtualenv.

  python -m pytest -q

Agents & LLMs

- The system uses a lightweight LLM provider wrapper to allow multi-model fallbacks (Groq/Gemini, etc.). The wrapper lives in `backend/agents/llm_provider.py` and can be extended to add retries and model selection logic.

Common issues

- "cannot call asyncio.run() from a running event loop": indicates an async/sync mismatch in agent code — see `fact_checker` and `forensic_expert` for synchronous wrappers.
- Missing or malformed evidence: ensure the Tavily API key is present and search responses are not rate-limited.


## Deployment

Render

- This repo includes `render.yaml` that defines two services: `aletheia-backend` and `aletheia-frontend`.
- The backend service uses the `backend/Dockerfile`; set the required environment variables (GROQ_API_KEY, TAVILY_API_KEY, APTOS_PRIVATE_KEY) in the Render dashboard.

Other

- You can deploy using any container platform (Docker Hub -> Kubernetes / Fly.io / Render). Ensure secrets are injected securely and set PORT for the backend container if required.


## Security & operational considerations

- Secrets management: use a secret manager for production keys; never store private keys in the repository.
- Rate limiting and input sanitization: the API implements simple rate limiting and input filters. For production, run behind an API gateway with stronger rate limiting and RBAC.
- LLM quotas: LLM providers may rate-limit or charge per token — configure retries and backoff in `llm_provider`.


## Contributing

Contributions are welcome. Suggested workflow:

1. Fork the repository
2. Create a feature branch
3. Run tests and linters locally
4. Submit a PR with a clear description and small, focused changes

Developer tips

- When modifying agents, keep prompts and evidence formats stable across `api_v2.py`, `ai_council.py`, and front-end components to avoid mismatch bugs.
- Add or update tests that cover the new behavior (happy path + at least one edge case).


## License

This project does not include a license file in the repository snapshot. Add a `LICENSE` file (for example MIT) if you want to make the project open source. If you need a recommendation, MIT is a permissive choice.


## Acknowledgements

- Tavily for search tooling
- Groq / Gemini for LLM backends
- Shelby Protocol for decoupled PDF/evidence storage


---

If you'd like, I can commit this updated README for you, run the backend tests, and push the change to origin/main. Tell me whether to (A) commit & push now, (B) run tests first, or (C) make further edits to the README.
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
