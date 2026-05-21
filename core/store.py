"""
DocChat Vector Store
ChromaDB wrapper — persist, list, delete documents.
WHY local ChromaDB: zero cloud dependency, zero cost beyond API key,
works offline after first embed, persistent across sessions.
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path

CHROMA_DIR = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "docchat"


def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def list_documents() -> list[str]:
    """Return list of unique document names indexed."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.get(include=["metadatas"])
    names = list({m.get("source", "unknown") for m in results["metadatas"]})
    return sorted(names)


def delete_document(filename: str):
    """Delete all chunks belonging to a specific document."""
    collection = get_collection()
    results = collection.get(include=["metadatas"])
    ids_to_delete = [
        id_ for id_, meta in zip(results["ids"], results["metadatas"])
        if meta.get("source") == filename
    ]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def clear_all():
    """Wipe entire vector store."""
    client = get_client()
    client.delete_collection(COLLECTION_NAME)


def get_chunk_count() -> int:
    return get_collection().count()
