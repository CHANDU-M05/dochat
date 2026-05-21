# dochat 🗂️

Chat with your PDFs — a production-ready RAG chatbot built with FastAPI, ChromaDB, and Streamlit.
Supports multiple LLM providers: Gemini, OpenAI, and Anthropic Claude.

---

## Features

- **Multi-provider LLM** — Gemini, OpenAI, Anthropic (switch via UI)
- **Persistent vector store** — ChromaDB local storage
- **Source citations** — every answer cites the exact PDF chunk
- **Per-document management** — upload, list, delete individual PDFs
- **Clean REST API** — `/ingest`, `/ask`, `/documents`, `/health`
- **One-command startup** — `./run.sh`

---

## Quick Start

```bash
git clone https://github.com/CHANDU-M05/dochat
cd dochat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Open **http://localhost:8501**

---

## Architecturechroma_db
---

## Usage
---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service status + chunk count |
| POST | `/ingest` | Upload and index a PDF |
| POST | `/ask` | Ask a question |
| GET | `/documents` | List indexed documents |
| DELETE | `/documents/{name}` | Remove a document |
| DELETE | `/clear` | Wipe entire vector store |

---

## Environment Variables

```bash
DOCHAT_API_URL=http://localhost:8000
LLM_PROVIDER=gemini
CHROMA_DB_PATH=./chroma_db
```

---

## Project Structurechroma_db---

## License

MIT
