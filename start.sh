#!/bin/bash

# Start FastAPI on port 8000 in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Wait briefly for FastAPI to initialize
sleep 5

# Start Streamlit on port 7860 (Hugging Face default port)
streamlit run frontend.py --server.port=7860 --server.address=0.0.0.0
