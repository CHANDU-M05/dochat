"""
DocChat Retriever
Query → vector search → LLM → answer + sources.
WHY show sources: every answer cites exact page + filename.
Hallucination drops to near zero when LLM is forced to answer
only from retrieved context. Sources make that verifiable.
"""

from store import get_collection


SYSTEM_PROMPT = """You are DocChat, an expert document assistant.
Answer the user's question using ONLY the context provided below.
Rules:
- If the answer is in the context, answer clearly and completely
- If the answer is NOT in the context, say exactly: "I could not find this in the uploaded documents."
- Never make up information not present in the context
- Be concise but thorough
- Always cite which document and page your answer comes from

Context:
{context}"""


def retrieve_chunks(
    query: str,
    api_key: str,
    provider: str = "gemini",
    k: int = 4,
) -> list[dict]:
    """
    Embed query, run similarity search, return top-k chunks with metadata.
    WHY k=4: sweet spot — enough context, under token limits.
    """
    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        embedder = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key,
        )
    else:
        from langchain_openai import OpenAIEmbeddings
        embedder = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key,
        )

    query_embedding = embedder.embed_query(query)

    collection = get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", "?"),
            "score": round(1 - dist, 3),  # cosine similarity
        })

    return chunks


def generate_answer(
    query: str,
    chunks: list[dict],
    api_key: str,
    provider: str = "gemini",
    history: list[dict] = None,
) -> dict:
    """
    Build context from chunks, call LLM, return answer + sources.
    """
    if not chunks:
        return {
            "answer": "No documents indexed yet. Upload a PDF first.",
            "sources": [],
        }

    # Build context string
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}: {chunk['source']}, Page {chunk['page']}]\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)

    system = SYSTEM_PROMPT.format(context=context)

    # Build messages with history
    messages = []
    if history:
        for h in history[-4:]:  # last 4 exchanges for context
            messages.append({"role": "user", "content": h["question"]})
            messages.append({"role": "assistant", "content": h["answer"]})
    messages.append({"role": "user", "content": query})

    # Call LLM
    try:
        if provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=system,
            )
            # Build chat history for Gemini
            gemini_history = []
            for h in history[-4:] if history else []:
                gemini_history.append({"role": "user", "parts": [h["question"]]})
                gemini_history.append({"role": "model", "parts": [h["answer"]]})

            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(query)
            answer = response.text.strip()

        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            all_messages = [{"role": "system", "content": system}] + messages
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=all_messages,
                max_tokens=1000,
                temperature=0.1,
            )
            answer = response.choices[0].message.content.strip()

    except Exception as e:
        answer = f"LLM error: {e}"

    # Deduplicate sources
    seen = set()
    sources = []
    for chunk in chunks:
        key = f"{chunk['source']}_p{chunk['page']}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "file": chunk["source"],
                "page": chunk["page"],
                "score": chunk["score"],
            })

    return {"answer": answer, "sources": sources}


def ask(
    query: str,
    api_key: str,
    provider: str = "gemini",
    history: list[dict] = None,
    k: int = 4,
) -> dict:
    """Main entry point — retrieve + generate."""
    chunks = retrieve_chunks(query, api_key, provider, k)
    return generate_answer(query, chunks, api_key, provider, history)
