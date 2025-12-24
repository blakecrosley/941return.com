#!/bin/bash

# Kill any existing server on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Activate virtual environment and start server
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
