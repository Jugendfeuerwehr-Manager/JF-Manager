#!/bin/bash

# Production deployment script with zero-downtime deployment strategy

set -e

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
BLUE_COMPOSE="docker-compose $COMPOSE_FILES"

echo "======================================"
echo "JF-Manager Blue-Green Deployment"
echo "======================================"
echo ""

# Pre-deployment checks
echo "Running pre-deployment checks..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    exit 1
fi

echo "✓ Pre-deployment checks passed"
echo ""

# Create backup before deployment
echo "Creating pre-deployment backup..."
$BLUE_COMPOSE run --rm backup
echo "✓ Backup created"
echo ""

# Pull latest images
echo "Pulling latest images..."
$BLUE_COMPOSE pull
echo "✓ Images pulled"
echo ""

# Build images if needed
echo "Building images..."
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export VCS_REF=$(git rev-parse --short HEAD)
$BLUE_COMPOSE build --no-cache
echo "✓ Images built"
echo ""

# Start new containers
echo "Starting new containers..."
$BLUE_COMPOSE up -d --remove-orphans
echo "✓ New containers started"
echo ""

# Wait for services to be healthy
echo "Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker-compose ps | grep -q "unhealthy"; then
        echo "Waiting... ($ELAPSED seconds)"
        sleep 5
        ELAPSED=$((ELAPSED + 5))
    else
        break
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "❌ Services failed to become healthy within $MAX_WAIT seconds"
    echo "Rolling back..."
    $BLUE_COMPOSE down
    exit 1
fi

echo "✓ All services are healthy"
echo ""

# Run migrations
echo "Running database migrations..."
$BLUE_COMPOSE exec -T backend python manage.py migrate --noinput
echo "✓ Migrations completed"
echo ""

# Collect static files
echo "Collecting static files..."
$BLUE_COMPOSE exec -T backend python manage.py collectstatic --noinput
echo "✓ Static files collected"
echo ""

# Health check
echo "Performing health checks..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✓ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    exit 1
fi

if curl -f http://localhost/api/v1/ > /dev/null 2>&1; then
    echo "✓ Backend health check passed"
else
    echo "❌ Backend health check failed"
    exit 1
fi

echo ""

# Cleanup old images
echo "Cleaning up old images..."
docker image prune -f
echo "✓ Cleanup completed"
echo ""

echo "======================================"
echo "✓ Deployment Successful!"
echo "======================================"
echo ""
echo "Application Status:"
$BLUE_COMPOSE ps
echo ""
echo "Access your application at:"
echo "  Frontend: http://$(hostname -f)"
echo "  Admin:    http://$(hostname -f)/admin"
echo ""
