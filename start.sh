#!/bin/bash

# Start FastAPI on port 8000 in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Waiting for FastAPI to initialize..."

# Poll port 8000 until http://127.0.0.1:8000/ returns status 200
# 200 is 'okay status' so that front end starts after backend is fully operational
until python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" 2>/dev/null; do
  sleep 2
done

echo "FastAPI is up! Starting Streamlit..."

# Start Streamlit on port 7860
streamlit run frontend.py --server.port=7860 --server.address=0.0.0.0
