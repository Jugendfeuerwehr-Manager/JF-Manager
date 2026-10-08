#!/bin/bash

# Quick start for local development. Secrets come from backend/.env
# (git-ignored); see docs/getting-started.md.

set -e

echo "🚀 Starting JF-Manager Development Environment"
echo ""

if [ ! -f "backend/Pipfile" ]; then
    echo "❌ Backend Pipfile not found"
    exit 1
fi

if [ ! -f "backend/.env" ]; then
    echo "❌ backend/.env fehlt. Vorlage kopieren und ausfüllen:"
    echo "   cp backend/example.env backend/.env"
    echo "   Details: docs/getting-started.md"
    exit 1
fi

for required in DJANGO_SECRET_KEY FIELD_ENCRYPTION_KEY; do
    if ! grep -Eq "^${required}=.+" backend/.env; then
        echo "❌ ${required} fehlt in backend/.env (siehe docs/getting-started.md)."
        exit 1
    fi
done

if ! grep -Eqi "^DEBUG=(true|1|yes)" backend/.env; then
    echo "⚠️  DEBUG=True fehlt in backend/.env: Cookies wären 'Secure' und der Login über http scheitert."
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    (cd frontend && npm install)
fi

set +e

echo "🗄  Applying database migrations"
(cd backend && pipenv run python manage.py migrate) || exit 1

if command -v redis-cli >/dev/null 2>&1 && ! redis-cli -p 6379 ping >/dev/null 2>&1; then
    echo "🧰 Starting Redis without persistence on :6379"
    redis-server --port 6379 --save '' --appendonly no --daemonize yes >/dev/null
fi

# pipenv loads backend/.env automatically
echo "🐍 Starting Django backend on http://localhost:8000"
(cd backend && pipenv run python manage.py runserver 127.0.0.1:8000) > backend.log 2>&1 &
BACKEND_PID=$!

echo "⚙️  Starting background worker"
(cd backend && pipenv run python manage.py rqworker default) > worker.log 2>&1 &
WORKER_PID=$!

sleep 3

echo "⚡ Starting Vue.js frontend on http://localhost:5173"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "✅ Servers are starting!"
echo ""
echo "📍 App:      http://localhost:5173   ← im Browser immer diese Adresse öffnen"
echo "📍 Admin:    http://localhost:5173/admin/"
echo "📍 API:      http://localhost:8000/api/v1 (über Vite weitergeleitet)"
echo ""
echo "💡 Logs: tail -f backend.log worker.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
