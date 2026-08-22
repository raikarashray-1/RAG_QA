import streamlit as st
import requests
import uuid

# Set up clean page config
st.set_page_config(
    page_title="Goa Building Laws AI Assistant",
    page_icon="🏛️",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000/chat"

# --- Sidebar: Purpose & Controls ---
with st.sidebar:
    st.header("About This Tool 🏛️")
    st.markdown(
        """
        Designed to help **architects**, **urban planners**, and **builders** 
        effortlessly navigate and understand the official **Goa Building Regulations** 
        without digging through dense legal texts and planning documents.
        """
    )
    st.divider()
    
    # Quick session reset option in sidebar
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.session_active = True
        st.rerun()

# --- Main Interface ---
st.title("🏛️ Goa Building Regulations AI Assistant")
st.caption("Ask questions about Goa Building Regulations 2018 or type 'quit' to end the session.")

# Initialize session states
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_active" not in st.session_state:
    st.session_state.session_active = True

# 1. Render all stored messages in history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Render input box if session is active
if st.session_state.session_active:
    if user_query := st.chat_input("Ask about FAR, setbacks, height restrictions, etc..."):
        
        # Display user message immediately in UI
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Call FastAPI backend
        payload = {
            "query": user_query,
            "thread_id": st.session_state.thread_id
        }
        
        try:
            with st.spinner("Searching regulations..."):
                res = requests.post(API_URL, json=payload, timeout=30)

            if res.status_code == 200:
                response = res.json()

                if response.get("is_exit"):
                    st.session_state.session_active = False
                    st.rerun()
                else:
                    bot_answer = response.get("answer", "No answer provided.")
                    st.session_state.messages.append({"role": "assistant", "content": bot_answer})
                    with st.chat_message("assistant"):
                        st.markdown(bot_answer)
            else:
                st.error(f"Backend Error ({res.status_code}): {res.text}")

        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to backend service: {e}")

# 3. Session ended notice
else:
    st.warning("👋 Chat session ended. Click 'Reset Conversation' in the sidebar or refresh to start a new chat.")
