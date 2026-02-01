#!/bin/bash

# HawkEye2 - Quick Run Script
# This script starts the backend server

echo "============================================"
echo "  HawkEye2 - Drone Surveillance System"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/app/best.pt" ]; then
    echo "❌ Error: best.pt not found!"
    echo "   Make sure you're running this from the hawk-eye2 directory"
    echo "   and that backend/app/best.pt exists"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found!"
    echo "   Creating new virtual environment..."
    python3 -m venv .venv
    echo "   Installing dependencies..."
    .venv/bin/pip install -r backend/app/requirements.txt
fi

# Activate virtual environment and start server
echo "🚀 Starting backend server..."
echo ""
echo "   Backend: http://localhost:8000"
echo "   WebSocket: ws://localhost:8000/ws"
echo ""
echo "📂 Open frontend/index.html in your browser"
echo "   Or run: python3 -m http.server 8080 (in frontend directory)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================"

cd backend
source ../.venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
