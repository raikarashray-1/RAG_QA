#!/bin/bash

# Start FastAPI on port 8000 in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Waiting for FastAPI to initialize..."

# Poll port 8000 until FastAPI returns a response
until curl -s http://127.0.0.1:8000/ > /dev/null; do
  sleep 2
done

echo "FastAPI is up! Starting Streamlit..."

# Start Streamlit on port 7860
streamlit run frontend.py --server.port=7860 --server.address=0.0.0.0
