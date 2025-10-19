
import streamlit as st
from backend import (
    chatbot,
    retrieve_all_threads,
    save_thread_title,
    get_thread_title,
    generate_short_title,
    delete_thread,
    get_clean_state,
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid


# -------------------- Page Config --------------------
st.set_page_config(page_title="LangGraph Chatbot", page_icon="💬", layout="centered")


# -------------------- Utility Functions --------------------

def generate_thread_id():
    return str(uuid.uuid4())

def upsert_thread_front(thread_list, thread_id, title):
    """Insert or move a thread to the top (newest-first)."""
    filtered = [(tid, ttitle) for tid, ttitle in thread_list if tid != thread_id]
    return [(thread_id, title)] + filtered

def start_new_chat():
    """Create a new chat placeholder and set it active."""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []
    st.session_state['thread_title'] = "New Chat"
    st.session_state['pending_new_thread'] = True

    # Add to sidebar (top)
    if thread_id not in [t[0] for t in st.session_state['chat_threads']]:
        st.session_state['chat_threads'] = upsert_thread_front(
            st.session_state['chat_threads'], thread_id, "New Chat"
        )

def load_conversation(thread_id):
    """Load messages (excluding tool traces)."""
    messages = get_clean_state(thread_id)
    result = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            continue
        role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
        result.append({'role': role, 'content': getattr(msg, "content", "")})
    return result


# -------------------- Session Setup --------------------

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

raw_threads = retrieve_all_threads() or []
st.session_state['chat_threads'] = list(raw_threads)

if 'thread_title' not in st.session_state:
    st.session_state['thread_title'] = "New Chat"

if 'pending_new_thread' not in st.session_state:
    st.session_state['pending_new_thread'] = True  # ✅ Always treat initial load as new chat

if 'menu_open' not in st.session_state:
    st.session_state['menu_open'] = {}


# -------------------- Sidebar --------------------

st.sidebar.title("💬 LangGraph Chatbot")

if st.sidebar.button("➕ New Chat"):
    start_new_chat()

st.sidebar.subheader("🗂️ My Conversations")

for thread_id, title in st.session_state['chat_threads']:
    cols = st.sidebar.columns([0.85, 0.15])

    # Load chat
    if cols[0].button(title, key=f"{thread_id}_btn"):
        st.session_state['thread_id'] = thread_id
        st.session_state['thread_title'] = title
        st.session_state['pending_new_thread'] = title == "New Chat"
        st.session_state['message_history'] = load_conversation(thread_id)
        st.session_state['chat_threads'] = upsert_thread_front(
            st.session_state['chat_threads'], thread_id, title
        )

    # Menu button
    if cols[1].button("⋮", key=f"{thread_id}_menu_btn"):
        st.session_state['menu_open'][thread_id] = not st.session_state['menu_open'].get(thread_id, False)

    # Delete option
    if st.session_state['menu_open'].get(thread_id, False):
        with st.sidebar.container():
            st.markdown(f"**Options for '{title}'**")
            if st.button("🗑️ Delete", key=f"{thread_id}_delete_btn"):
                delete_thread(thread_id)
                st.session_state['chat_threads'] = [
                    (tid, ttitle)
                    for tid, ttitle in st.session_state['chat_threads']
                    if tid != thread_id
                ]
                st.session_state['menu_open'][thread_id] = False
                if st.session_state['thread_id'] == thread_id:
                    start_new_chat()  # ✅ Start fresh after deleting active thread


# -------------------- Main Chat UI --------------------

st.title("🤖 LangGraph Chatbot")
st.markdown("Welcome to your **AI-powered assistant** built with LangChain + Streamlit 🚀")

# Empty chat intro message
if not st.session_state['message_history']:
    st.info("💬 Start typing below to begin a new conversation or click **New Chat** to create another thread.")

# Show chat history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

# User input box
user_input = st.chat_input("Type your message here...")

if user_input:
    # ✅ Ensure we have a valid thread for this new message
    if st.session_state.get('pending_new_thread', False):
        thread_id = st.session_state['thread_id']
        if thread_id not in [t[0] for t in st.session_state['chat_threads']]:
            st.session_state['chat_threads'] = upsert_thread_front(
                st.session_state['chat_threads'], thread_id, "New Chat"
            )

    # Add user message
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # Auto-generate title for new chat
    if st.session_state.get('pending_new_thread', False):
        first_msg = st.session_state['message_history'][0]['content']
        logical_title = generate_short_title(first_msg)
        save_thread_title(st.session_state['thread_id'], logical_title)
        st.session_state['thread_title'] = logical_title
        st.session_state['pending_new_thread'] = False

        # Update sidebar title instantly
        st.session_state['chat_threads'] = upsert_thread_front(
            st.session_state['chat_threads'],
            st.session_state['thread_id'],
            logical_title
        )

     

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    # ---------------- Stream AI Response ----------------
    with st.chat_message('assistant'):
        def ai_stream():
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            ):
                if isinstance(message_chunk, ToolMessage):
                    continue
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_stream())

    # Save AI response
    if ai_message:
        st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
        # Refresh sidebar order
        try:
            current_title = get_thread_title(st.session_state['thread_id']) or st.session_state['thread_title']
        except Exception:
            current_title = st.session_state['thread_title']
        st.session_state['chat_threads'] = upsert_thread_front(
            st.session_state['chat_threads'],
            st.session_state['thread_id'],
            current_title
        )
