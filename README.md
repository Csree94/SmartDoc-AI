# SmartDoc AI - RAG Chatbot with Web Search

## Overview

SmartDoc AI is a web-based AI chatbot that answers questions using users' uploaded documents and searches the web when additional information is needed.

The application combines Retrieval-Augmented Generation (RAG), vector similarity search, and web search to provide answers with source citations.

## Features

- Upload PDF and TXT documents.
- Extract and split document text into chunks.
- Generate document embeddings using the Gemini API.
- Store and retrieve embeddings using PostgreSQL and pgvector.
- Answer questions using relevant document passages.
- Search the web when the uploaded documents do not provide relevant information.
- Display document citations and web-source links.
- Use a web-based chat interface built with React and TypeScript.

## Technology Stack

**Backend**
- Python
- FastAPI
- Gemini API
- PostgreSQL with pgvector
- psycopg (PostgreSQL driver)
- DuckDuckGo web search

**Frontend**
- React
- TypeScript
- Vite
- React Markdown

## Project Structure

```text
SmartDoc-AI/
|-- backend/
|   |-- config.py
|   |-- db.py
|   |-- rag.py
|   |-- main.py
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |-- package.json
|   `-- .env.example
|-- tests/
|   `-- test_backend.py
|-- .env.example
|-- .gitignore
`-- README.md
```

## Prerequisites

- Python installed
- Node.js and npm installed
- A PostgreSQL database with pgvector support (for example, a free Neon PostgreSQL database)
- An API key for Gemini

NVIDIA API credentials may also be required if the optional fallback model is enabled.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Csree94/SmartDoc-AI.git
cd SmartDoc-AI
```

### 2. Configure environment variables

The root `.env.example` is a template for the root `.env` file. Copy it and fill in real values:

```powershell
copy .env.example .env
```

It contains placeholders such as `GEMINI_API_KEY` (your Gemini API key) and `DATABASE_URL` (your PostgreSQL/Neon connection string).

Real credentials and database passwords must never be committed to GitHub. They live only in the local `.env` file, which is excluded from Git by `.gitignore`.

### 3. Set up the Python environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

On Linux/macOS, use `.venv/bin/activate` instead of `.venv\Scripts\Activate.ps1`.

### 4. Start the backend

The backend entry point is `backend.main:app`, so the startup command is:

```powershell
uvicorn backend.main:app --reload --port 8000
```

If `uvicorn` is not on your PATH with the virtual environment active, run it through Python:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

### 5. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
```

The backend address is configured through the frontend environment file. `frontend/.env.example` contains the setting used by this project:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If your backend runs at this same address, no change is needed. Otherwise, copy `frontend/.env.example` to `frontend/.env` and adjust the value, then start the development server:

```powershell
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

## How to Use

1. Open SmartDoc AI in your browser.
2. Upload a PDF or TXT document.
3. Wait for the document indexing confirmation.
4. Ask a question about the uploaded document.
5. Review the answer and its document citations.
6. Ask a question requiring external information to see the web-search functionality and source links.

## Retrieval-Augmented Generation

SmartDoc AI implements a document retrieval pipeline rather than sending every question directly to an LLM.

The application extracts document text, splits it into chunks, generates embeddings, and stores them in PostgreSQL with pgvector. When a question is asked, relevant document chunks are retrieved and used as context for answer generation.

When relevant document information is unavailable, the application can use web search to obtain additional evidence.

## Security

- Keep API keys and database credentials in the local `.env` file.
- Never commit real credentials to GitHub.
- Use `.env.example` (root and frontend) as configuration templates only.

## Project Repository

https://github.com/Csree94/SmartDoc-AI
