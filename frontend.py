# Most of the Code is AI generated, steps commented
import streamlit as st
import requests
import uuid

API_URL = "http://127.0.0.1:8000/chat"

st.title("RAG Assistant - Building Laws")

# Show instructions at the top
st.info("Ask me anything about Goa Building Regulations 2018, or type 'q' to end the session.")

# Initialize session states
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_active" not in st.session_state:
    st.session_state.session_active = True

# 1. Render existing chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Render input box ONLY if session is still active
if st.session_state.session_active:
    if user_query := st.chat_input("Ask a question..."):
        
        # Call FastAPI backend passing query AND thread_id
        payload = {
            "query": user_query,
            "thread_id": st.session_state.thread_id
        }
        res = requests.post(API_URL, json=payload)

        if res.status_code == 200:
            response = res.json()

            # IF USER EXIT: Only show the termination alert once
            if response.get("is_exit"):
                st.session_state.session_active = False
                st.warning("👋 Chat session ended. Refresh the page to start a new chat.")
                st.rerun()  # Instantly hides the input box
            
            # IF REGULAR QUESTION: Append user message & assistant reply to UI
            else:
                st.session_state.messages.append({"role": "user", "content": user_query})
                st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
                
                with st.chat_message("user"):
                    st.markdown(user_query)
                with st.chat_message("assistant"):
                    st.markdown(response["answer"])
        else:
            # Display readable error message on screen instead of crashing
            st.error(f"Backend Error ({res.status_code}): {res.text}")

# 3. If session ended previously, display closed status banner
else:
    st.warning("👋 Chat session ended. Refresh the page to start a new chat.")
