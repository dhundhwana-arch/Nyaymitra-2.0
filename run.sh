#!/bin/bash
echo "=========================================================="
echo " Starting JARVIS AI Justice Access & Navigation System    "
echo " Developer: Divyesh Bambhaniya                            "
echo "=========================================================="

# Start backend if python is available
cd backend
if command -v python3 &> /dev/null; then
    echo "Installing backend requirements..."
    pip install -r requirements.txt
    echo "Starting FastAPI Server on http://127.0.0.1:8000..."
    python3 main.py &
    BACKEND_PID=$!
fi

cd ..
echo "Starting Frontend Web Server on http://localhost:3000..."
cd frontend
python3 -m http.server 3000
