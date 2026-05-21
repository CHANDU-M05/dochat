"""
dochat — FastAPI backend
Endpoints: /ingest /ask /documents /documents/{name} /clear /health
"""

import sys
sys.path.insert(0, ".")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated

from store import get_chunk_count, list_documents, delete_document, clear_all
from ingestor import ingest_pdf
from retriever import ask

app = FastAPI(title="dochat", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str
    api_key: str
    provider: str = "gemini"
    history: list[dict] = []
    k: int = 4

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "chunks_indexed": get_chunk_count()}


@app.get("/documents")
def get_documents():
    return {
        "documents": list_documents(),
        "total_chunks": get_chunk_count(),
    }


@app.post("/ingest")
async def ingest(
    file: Annotated[UploadFile, File()],
    api_key: Annotated[str, Form()],
    provider: Annotated[str, Form()] = "gemini",
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 20 MB.")

    result = ingest_pdf(
        file_bytes=file_bytes,
        filename=file.filename,
        api_key=api_key,
        provider=provider,
    )

    if not result["success"]:
        raise HTTPException(status_code=422, detail=result.get("error", "Ingestion failed."))

    return result


@app.post("/ask")
def ask_question(body: AskRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    return ask(
        query=body.query,
        api_key=body.api_key,
        provider=body.provider,
        history=body.history,
        k=body.k,
    )


@app.delete("/documents/{filename}")
def remove_document(filename: str):
    deleted = delete_document(filename)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"'{filename}' not found.")
    return {"deleted_chunks": deleted, "filename": filename}


@app.delete("/clear")
def wipe_all():
    clear_all()
    return {"status": "cleared"}
