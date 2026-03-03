# Bible RAG - Setup Guide

Complete installation and configuration guide for local development.

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites Installation](#prerequisites-installation)
- [Local Development Environment](#local-development-environment)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Data Ingestion](#data-ingestion)
- [Embedding Generation](#embedding-generation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Hardware

**Minimum Requirements:**
- CPU: 4+ cores (Intel i5/AMD Ryzen 5 or equivalent)
- RAM: 8GB
- Storage: 20GB free space
- Internet: Stable connection for downloading models and data

**Recommended Requirements:**
- CPU: 8+ cores (Intel i7/AMD Ryzen 7, Apple M1/M2/M3/M4)
- RAM: 16GB (embedding model ~4GB + reranker ~500MB + OS + DB)
- Storage: 50GB SSD
- GPU: Optional (speeds up embedding 3-5x, but not required)

### Operating Systems

- **macOS**: 12.0+ (Monterey or later)
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+
- **Windows**: Windows 10/11 with WSL2 (recommended) or native

---

## Prerequisites Installation

### 1. Python 3.12+

**macOS (using Homebrew):**
```bash
brew install python@3.12
python3.12 --version  # Verify installation
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
python3.12 --version
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"
- Verify: `python --version`

### 2. Node.js 22 LTS (or 20 LTS)

**macOS:**
```bash
brew install node@22
node --version  # Should be 22.x (LTS)
npm --version
```

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version
npm --version
```

**Windows:**
- Download from [nodejs.org](https://nodejs.org/)
- Install LTS version (22.x)
- Verify in PowerShell: `node --version`

### 3. Docker and Docker Compose

**macOS:**
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
# Or via Homebrew
brew install --cask docker
# Start Docker Desktop, then verify:
docker --version
docker compose version
```

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

**Windows:**
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)
- Ensure WSL2 backend is enabled
- Verify in PowerShell: `docker --version`

### 4. Git

**macOS:** `brew install git`
**Linux:** `sudo apt install git`
**Windows:** Download from [git-scm.com](https://git-scm.com/)

---

## Local Development Environment

### 1. Clone Repository

```bash
git clone https://github.com/calebyhan/bible-rag.git
cd bible-rag
ls -la  # Should see: backend/, frontend/, docs/, docker-compose.yml, README.md
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL + Redis in detached mode
docker compose up -d

# Verify services are running
docker compose ps

# Expected output:
# NAME                  STATUS
# bible-rag-postgres    Up
# bible-rag-redis       Up

# Check logs if needed
docker compose logs postgres
docker compose logs redis
```

**Default Service Ports:**
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

**Stop services when needed:**
```bash
docker compose down      # Stops containers (data persists in volumes)
docker compose down -v   # Stops containers AND deletes volumes (loses all data)
```

### 3. Database Initialization

The schema is created automatically when you first run the backend. You can verify connectivity with:

```bash
# Connect via Docker exec
docker exec -it bible-rag-postgres psql -U bible_user -d bible_rag

# Enable pgvector (if not done by docker-compose)
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
\dt    -- list tables (empty initially)
\q     -- quit
```

---

## Backend Setup

### 1. Create Virtual Environment

```bash
cd backend

# Create virtual environment (use .venv, not venv)
python3.12 -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Verify activation (should see (.venv) in prompt)
which python  # Should point to .venv/bin/python
```

### 2. Install Dependencies

```bash
# Ensure .venv is activated
pip install --upgrade pip
pip install -r requirements.txt

# Key packages installed:
# - fastapi, uvicorn (API server)
# - sqlalchemy, psycopg2-binary, asyncpg (database)
# - pgvector (vector extension client)
# - redis (caching)
# - sentence-transformers, torch (embedding model)
# - google-generativeai, groq (LLM APIs)
# - pydantic, pydantic-settings (data validation)

# Expected installation time: 5-15 minutes (downloads ~3GB including PyTorch)
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
nano .env  # or: code .env, vim .env
```

**Update `.env`:**

```env
# Database
DATABASE_URL=postgresql://bible_user:bible_password@localhost:5432/bible_rag
POSTGRES_USER=bible_user
POSTGRES_PASSWORD=bible_password
POSTGRES_DB=bible_rag

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys (get these from respective services)
GEMINI_API_KEY=your_gemini_api_key_here  # https://ai.google.dev/
GROQ_API_KEY=your_groq_api_key_here      # https://console.groq.com/

# Embedding model
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIMENSION=1024

# Reranker
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# Cache
CACHE_TTL=86400

# Search tuning (defaults are production-ready)
SIMILARITY_THRESHOLD=0.55
OVERRETRIEVE_FACTOR=3
RRF_K=60
ENABLE_QUERY_EXPANSION=true
ENABLE_HYBRID_SEARCH=true
ENABLE_RERANKING=true
RERANK_TOP_N=30
```

**Get API Keys:**

1. **Gemini API Key** (Free):
   - Visit https://ai.google.dev/
   - Sign in with Google account → "Get API Key" → Create new key

2. **Groq API Key** (Free):
   - Visit https://console.groq.com/
   - Sign up → API Keys → Create new key

### 4. Test Backend Server

```bash
# Ensure .venv is activated and PostgreSQL is running
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
```

**Test API in another terminal:**
```bash
# Health check (will show unhealthy until data is ingested)
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs  # Swagger UI
```

---

## Frontend Setup

### 1. Install Dependencies

```bash
# New terminal tab/window
cd frontend
npm install

# Key packages:
# - next 15, react 19, react-dom 19
# - typescript 5.7
# - tailwindcss 3
# - axios
# - aromanize (Korean romanization)

# Expected time: 1-3 minutes
```

### 2. Configure Environment Variables

```bash
cp .env.example .env.local
nano .env.local
```

**Update `.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Bible RAG
```

### 3. Start Development Server

```bash
npm run dev

# Expected output:
# ▲ Next.js 15.x.x
# - Local:    http://localhost:3000
# - Ready in 2.1s
```

Open http://localhost:3000 in your browser. You should see the chat interface.

---

## Data Ingestion

Data ingestion scripts live in `backend/scripts/`. Run each from the `backend/` directory with `.venv` activated.

### Step 1: Ingest Bible Translations

```bash
cd backend
source .venv/bin/activate

python scripts/data_ingestion.py

# This script:
# 1. Fetches 9 translations (NIV, ESV, NASB, KJV, WEB, KRV, RNKSV, ...)
# 2. Normalizes Unicode (NFC for Korean)
# 3. Inserts into translations, books, and verses tables
# 4. Loads cross-reference data (63,779+ links)
#
# Expected duration: 30-90 minutes (network-dependent)
# Expected output: ~31,000 verses × 9 translations
```

### Step 2: Ingest Original Languages

```bash
python scripts/original_ingestion.py

# This script:
# 1. Downloads OpenGNT Greek NT data
# 2. Downloads OSHB/WLC Hebrew OT data
# 3. Runs scripts/ingest_aramaic.py for Aramaic portions
# 4. Inserts 442,413 words into original_words table
#
# Expected duration: ~1-5 minutes
```

### Step 3: Verify Ingestion

```bash
# Connect to database
docker exec -it bible-rag-postgres psql -U bible_user -d bible_rag

# Check verse counts per translation
SELECT t.abbreviation, COUNT(v.id) as verse_count
FROM translations t
LEFT JOIN verses v ON t.id = v.translation_id
GROUP BY t.abbreviation
ORDER BY t.abbreviation;

# Check original language coverage
SELECT language, COUNT(*) as word_count
FROM original_words
GROUP BY language;

# Quit
\q
```

---

## Embedding Generation

Embeddings must be generated once for each stored verse. This is the most time-consuming setup step.

**Important Notes:**
- One-time process (only rerun when adding new translations)
- First run downloads the model (~2GB from Hugging Face)
- The reranker model (~500MB) is downloaded lazily on first query

### Generate Embeddings

```bash
cd backend
source .venv/bin/activate

python scripts/embeddings.py

# Expected output:
# Loading embedding model 'intfloat/multilingual-e5-large'...
# Downloading model (first run, ~2GB)...
# Model loaded!
# Fetching verses from database...
# Found 31,103 verses to embed
# Generating embeddings in batches of 32...
# [Progress bar...]
# Embedding generation complete! Total time: ~20-30 min
```

**Performance estimates:**
- Apple M-series CPU: ~5 minutes
- Intel i7 CPU: ~20-30 minutes
- NVIDIA GPU (CUDA): ~1-2 minutes

### Build Vector Index

```bash
docker exec -it bible-rag-postgres psql -U bible_user -d bible_rag
```

```sql
-- Create ivfflat index (takes 5-10 minutes for 31K vectors)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
ON embeddings
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);

-- Verify
\d embeddings

-- Run ANALYZE to update query planner statistics
ANALYZE embeddings;
ANALYZE verses;

\q
```

---

## Verification

### End-to-End Test

**1. Check all services are running:**
```bash
# Docker services
docker compose ps       # postgres + redis should be "Up"

# Terminal 1: Backend
uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

**2. Test API endpoints:**
```bash
# Health check
curl http://localhost:8000/health | python3 -m json.tool

# List translations
curl http://localhost:8000/api/translations | python3 -m json.tool

# Streaming search test (pipe through jq or process line by line)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"love and forgiveness","languages":["en"],"translations":["NIV"],"max_results":3}'
```

**3. Test frontend:**
1. Open http://localhost:3000
2. Enter search query: "What does Jesus say about love?"
3. Verify verse cards appear with results
4. Verify AI response streams in below the cards
5. Click "± Context" on a verse card — surrounding verses should appear
6. Click a Strong's number — "Find all verses" should open

**4. Test Korean search:**
1. Search: "사랑에 대한 예수님의 말씀"
2. Verify Korean text displays correctly with proper spacing
3. Enable Hanja/romanization toggle

---

## Troubleshooting

### Docker Services Won't Start

```bash
# Check Docker is running
docker info

# Check port conflicts (5432 or 6379)
lsof -i :5432   # macOS/Linux
lsof -i :6379

# If in use, stop conflicting services or change ports in docker-compose.yml

# Hard reset Docker
docker compose down -v
docker system prune -f
docker compose up -d
```

### Cannot Connect to PostgreSQL

```bash
# Verify running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Test connectivity
docker exec -it bible-rag-postgres pg_isready -U bible_user

# Verify DATABASE_URL in backend/.env
grep DATABASE_URL backend/.env
```

### pgvector Extension Error

```bash
docker exec -it bible-rag-postgres psql -U bible_user -d bible_rag
```
```sql
CREATE EXTENSION vector;
-- If error: rebuild Docker image
-- docker compose build --no-cache && docker compose up -d
```

### Embedding Model Download Fails

```bash
# Check internet connectivity
ping huggingface.co

# Set custom HF cache directory (if disk space issues)
export HF_HOME=/path/to/large/disk/hf_cache
python scripts/embeddings.py

# Use HF mirror (China/restricted networks)
export HF_ENDPOINT=https://hf-mirror.com
python scripts/embeddings.py
```

### Out of Memory During Embedding

```bash
# The embedding model requires ~4GB RAM. Reduce batch size if needed:
# Edit scripts/embeddings.py: batch_size = 16  (default 32)

# Monitor memory (macOS)
vm_stat | grep "Pages free"

# Linux
free -h

# Generate in chunks if needed
python scripts/embeddings.py --start-index 0 --end-index 10000
python scripts/embeddings.py --start-index 10000 --end-index 20000
```

### Frontend Won't Start

```bash
# Clear Next.js cache
rm -rf frontend/.next
rm -rf frontend/node_modules
cd frontend && npm install && npm run dev

# Check Node.js version (must be 18+, recommend 22)
node --version

# Check port conflicts
lsof -i :3000
# Run on different port: npm run dev -- -p 3001
```

### Korean Text Not Displaying

```bash
# Verify font loading in browser DevTools > Network (filter: "noto")
# Clear Next.js cache
rm -rf frontend/.next
npm run dev

# Check browser computed font-family on Korean element
# Must include Noto Sans KR
```

### API Rate Limit Errors (LLM)

The backend falls back from Gemini → Groq automatically. If both are rate-limited, verse results still return but without an AI response.

To bypass rate limits, provide your own API keys via the settings panel in the UI, or set `GEMINI_API_KEY` / `GROQ_API_KEY` in `backend/.env`.

### Streaming Search Returns No Results

```bash
# Check embeddings exist
docker exec -it bible-rag-postgres psql -U bible_user -d bible_rag -c "SELECT COUNT(*) FROM embeddings;"

# Check ivfflat index exists
docker exec -it bible-rag-postgres psql -U bible_user -d bible_rag \
  -c "\d embeddings"

# Re-run embedding generation if count is 0
python scripts/embeddings.py
```

### Getting Help

1. **Check logs**: `docker compose logs`, uvicorn terminal output, Next.js terminal output
2. **Enable debug logging**: set `DEBUG=true` in `backend/.env`, restart uvicorn with `--log-level debug`
3. **GitHub Issues**: https://github.com/calebyhan/bible-rag/issues

---

## Next Steps

After successful setup:

1. **Explore the API**: [docs/API.md](API.md)
2. **Learn the features**: [docs/FEATURES.md](FEATURES.md)
3. **Understand the architecture**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
4. **Deploy to production**: [docs/DEPLOYMENT.md](DEPLOYMENT.md)
