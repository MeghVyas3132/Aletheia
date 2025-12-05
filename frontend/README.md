
# MoveH Frontend

This is the frontend for MoveH, built with [Next.js](https://nextjs.org) and TypeScript. It provides a modern UI for AI-powered fact-checking, blockchain verification, and PDF report downloads.

## Features
- Next.js 14+ app directory
- Real-time claim verification via FastAPI backend
- Displays verdicts, sources, forensic analysis, and on-chain status
- Downloadable PDF reports via Shelby Protocol
- Modern, responsive UI with dark mode

## Getting Started

### 1. Install dependencies
```bash
pnpm install
# or
npm install
```

### 2. Configure environment
If you need to set API endpoints, create a `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run the development server
```bash
pnpm dev
# or
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure
- `app/` — Main Next.js app directory
- `components/` — UI components (SearchHero, VerificationResult, etc.)
- `public/` — Static assets
- `globals.css` — Global styles

## Integration
- Connects to the MoveH backend (`/backend/api.py`) for claim verification
- Displays blockchain verdicts and Shelby download links

## Deployment
You can deploy on [Vercel](https://vercel.com/) or any platform supporting Next.js.

## Troubleshooting
- Ensure the backend API is running and accessible
- Check CORS settings if you see network errors
- For Shelby downloads, ensure the backend returns the correct direct URL

## License
MIT

---
For backend setup, see [`../backend/README.md`](../backend/README.md).
