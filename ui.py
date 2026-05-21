"""
dochat — Streamlit UI
"""

import os
import requests
import streamlit as st

API_URL = os.getenv("DOCHAT_API_URL", "http://localhost:8000")

# ── Page config ───────────────────────────────────

st.set_page_config(
    page_title="dochat",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.user-bubble {
    background: #1a73e8; color: white;
    padding: 10px 14px;
    border-radius: 18px 18px 4px 18px;
    margin: 6px 0; max-width: 80%;
    float: right; clear: both; font-size: 15px;
}
.bot-bubble {
    background: #f1f3f4; color: #202124;
    padding: 10px 14px;
    border-radius: 18px 18px 18px 4px;
    margin: 6px 0; max-width: 80%;
    float: left; clear: both; font-size: 15px;
}
.source-chip {
    display: inline-block;
    background: #e8f0fe; color: #1a73e8;
    border-radius: 12px; padding: 2px 9px;
    font-size: 12px; margin: 2px 3px;
}
.clearfix { clear: both; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = []

# ── Helpers ───────────────────────────────────────

def refresh_docs():
    try:
        r = requests.get(f"{API_URL}/documents", timeout=5)
        data = r.json()
        st.session_state.indexed_docs = data.get("documents", [])
        return data.get("total_chunks", 0)
    except Exception:
        return 0

def format_history(messages):
    return [{"role": m["role"], "content": m["content"]} for m in messages]

# ── Sidebar ───────────────────────────────────────

with st.sidebar:
    st.title("🗂️ dochat")
    st.caption("Chat with your PDFs")
    st.divider()

    st.subheader("⚙️ Provider")
    provider = st.selectbox(
        "LLM Provider",
        options=["gemini", "openai", "anthropic"],
    )
    api_key = st.text_input(
        f"{provider.capitalize()} API Key",
        type="password",
        placeholder="Paste your API key...",
    )

    st.divider()

    st.subheader("📎 Upload PDFs")
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files and api_key:
        if st.button("⬆️ Ingest all", use_container_width=True):
            for f in uploaded_files:
                with st.spinner(f"Ingesting {f.name}…"):
                    try:
                        resp = requests.post(
                            f"{API_URL}/ingest",
                            files={"file": (f.name, f.read(), "application/pdf")},
                            data={"api_key": api_key, "provider": provider},
                            timeout=120,
                        )
                        result = resp.json()
                        if resp.status_code == 200:
                            st.success(f"✅ {f.name} — {result['chunks']} chunks")
                        else:
                            st.error(f"❌ {f.name}: {result.get('detail', 'Error')}")
                    except Exception as e:
                        st.error(f"❌ {f.name}: {e}")
            refresh_docs()
    elif uploaded_files and not api_key:
        st.warning("Enter your API key above first.")

    st.divider()

    st.subheader("📚 Indexed Documents")
    total_chunks = refresh_docs()

    if st.session_state.indexed_docs:
        st.caption(f"{len(st.session_state.indexed_docs)} files · {total_chunks} chunks")
        for doc in st.session_state.indexed_docs:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"📄 `{doc}`")
            if col2.button("🗑", key=f"del_{doc}"):
                r = requests.delete(f"{API_URL}/documents/{doc}")
                if r.status_code == 200:
                    st.toast(f"Removed {doc}", icon="🗑️")
                    refresh_docs()
                    st.rerun()
    else:
        st.info("No documents indexed yet.")

    st.divider()

    col1, col2 = st.columns(2)
    if col1.button("🗑 Clear all", use_container_width=True):
        requests.delete(f"{API_URL}/clear")
        refresh_docs()
        st.toast("Cleared", icon="🗑️")
        st.rerun()
    if col2.button("💬 New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Main chat ─────────────────────────────────────

st.markdown("## 💬 Chat")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">{msg["content"]}</div><div class="clearfix"></div>',
            unsafe_allow_html=True,
        )
    else:
        source_html = ""
        if msg.get("sources"):
            chips = "".join(
                f'<span class="source-chip">📄 {s["file"]} p.{s["page"]}</span>'
                for s in msg["sources"]
            )
            source_html = f'<div style="margin-top:6px">{chips}</div>'
        st.markdown(
            f'<div class="bot-bubble">{msg["content"]}{source_html}</div><div class="clearfix"></div>',
            unsafe_allow_html=True,
        )

st.divider()

with st.form("chat_form", clear_on_submit=True):
    cols = st.columns([8, 1])
    user_input = cols[0].text_input(
        "Message",
        placeholder="Ask anything about your documents…",
        label_visibility="collapsed",
    )
    submitted = cols[1].form_submit_button("Send", use_container_width=True)

if submitted and user_input.strip():
    if not api_key:
        st.error("Enter your API key in the sidebar.")
        st.stop()
    if not st.session_state.indexed_docs:
        st.warning("Upload and ingest a PDF first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Thinking…"):
        try:
            resp = requests.post(
                f"{API_URL}/ask",
                json={
                    "query": user_input,
                    "api_key": api_key,
                    "provider": provider,
                    "history": format_history(st.session_state.messages[:-1]),
                    "k": 4,
                },
                timeout=60,
            )
            data = resp.json()
            if resp.status_code == 200:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["answer"],
                    "sources": data.get("sources", []),
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ {data.get('detail', 'Error')}",
                    "sources": [],
                })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"⚠️ Connection error: {e}",
                "sources": [],
            })

    st.rerun()
