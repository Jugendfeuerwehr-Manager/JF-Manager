#!/bin/bash

# Quick start script for JF-Manager development

echo "🚀 Starting JF-Manager Development Environment"
echo ""

# Check if backend Pipfile exists
if [ ! -f "backend/Pipfile" ]; then
    echo "❌ Backend Pipfile not found"
    exit 1
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Start backend in background (run from backend directory!)
echo "🐍 Starting Django backend on http://localhost:8000"
(cd backend && pipenv run python manage.py runserver) > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "⚡ Starting Vue.js frontend on http://localhost:5173"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both servers are starting!"
echo ""
echo "📍 Backend:  http://localhost:8000"
echo "📍 Frontend: http://localhost:5173"
echo "📍 Admin:    http://localhost:8000/admin"
echo ""
echo "💡 Backend logs: tail -f backend.log"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
