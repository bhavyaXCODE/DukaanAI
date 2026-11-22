# DukaanAI – The Intelligent Voice Khata

> **Your shop. Your language. Your voice.**

A multilingual, AI-powered, voice-first digital khata system for Indian kirana shopkeepers.

**Team:** Lumina | **Team ID:** team-35486329053E  
**College:** JSS Science and Technology University, Mysuru  
**Hackathon:** Gnani Voice Hackathon – PS2: Voice Khata  

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop (for PostgreSQL)

### 1. Start PostgreSQL

```powershell
docker-compose up -d
```

Wait for healthy status:
```powershell
docker ps  # postgres should show "healthy"
```

### 2. Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Configure your API keys** in `backend/.env`:
```
GEMINI_API_KEY=your_google_gemini_api_key   # Optional - mock mode works without it
MOCK_VOICE=true                              # Uses browser Web Speech API
```

Seed the database:
```powershell
python seed_data.py
```

Start the server:
```powershell
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend Setup

```powershell
cd frontend
npm install
npm start
```

App opens at: http://localhost:3000

---

## Voice Mode

### Mock Mode (Default – MOCK_VOICE=true)
- **STT:** Browser Web Speech API (Chrome recommended)
- **TTS:** Browser `speechSynthesis`
- No Gnani API keys needed
- Works immediately out of the box

### Real Mode (MOCK_VOICE=false)
- **STT:** Gnani Prisma v3.0
- **TTS:** Gnani Timbre v3.0
- Requires `GNANI_STT_API_KEY` and `GNANI_TTS_API_KEY` in `.env`
- Also requires `GEMINI_API_KEY` for LLM NLU

---

## Features

| Feature | Description |
|---|---|
| 🎙️ Voice Khata | Speak credit/payment transactions naturally |
| 🌐 Multilingual | Kannada, Hindi, English, code-mixed speech |
| ✅ Confirmation | Every transaction confirmed before saving |
| 👥 Smart Resolution | Disambiguates customers with same name |
| 💬 Ledger Queries | "Ramesh ka kitna baaki hai?" by voice |
| 🔄 Draft Recovery | Incomplete transactions never lost |
| 📊 Dashboard | Live stats, 7-day credit vs payment chart |

---

## Architecture

```
Browser (React) ←→ WebSocket ←→ FastAPI Backend ←→ PostgreSQL
                                      ↓
                           Gnani STT / LLM / Gnani TTS
```

**Voice Pipeline Stages:**
1. Browser Mic → WebSocket stream
2. Gnani Prisma v3.0 STT (or browser Web Speech API in mock mode)
3. Google Gemini NLU (intent + entity extraction)
4. Customer Resolver (fuzzy matching + landmark disambiguation)
5. Transaction Validator (confirmation prompt)
6. PostgreSQL write (after shopkeeper confirms)
7. Gnani Timbre v3.0 TTS response (or browser speechSynthesis in mock mode)

---

## Demo Data

The seed script creates:
- **Shop:** Shri Lakshmi Kirana Store (owner: santhoshini, language: Kannada)
- **12 Customers** including two "Ramesh" customers for disambiguation demo
- **Transactions** producing dashboard values: ₹15,028 outstanding, ₹1,660 credit today, 5 transactions today

---

## Project Structure

```
├── docker-compose.yml      # PostgreSQL 15
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI entrypoint
│   │   ├── core/           # Config, DB setup
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── api/            # REST route handlers
│   │   ├── services/       # Voice pipeline processors
│   │   └── websocket/      # WebSocket handler
│   ├── seed_data.py        # Demo data seeder
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/          # Dashboard, VoiceKhata, Customers, etc.
        ├── components/     # Sidebar, StatCard, VoiceButton, etc.
        ├── hooks/          # useVoiceWebSocket, useSpeechRecognition
        ├── context/        # AppContext, VoiceContext
        └── services/       # API client
```

---

## Responsible AI

- AI disclosure shown at first Voice Khata session
- Every financial transaction requires explicit voice confirmation
- Demo data uses synthetic/fictional personas only
- No lending decisions, no pressure-based reminders
- Credentials managed via `.env` only

---

*DukaanAI – Real people. Real conversations. Real financial control.*
