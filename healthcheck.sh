#!/bin/bash

# Health check script for monitoring

set -e

COMPOSE_FILES="-f docker-compose.yml"
if [ -f docker-compose.prod.yml ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
fi

echo "======================================"
echo "JF-Manager Health Check"
echo "======================================"
echo "Timestamp: $(date)"
echo ""

# Check if containers are running
echo "Container Status:"
docker-compose $COMPOSE_FILES ps
echo ""

# Check container health
echo "Health Checks:"
echo ""

# Frontend
if curl -sf http://localhost/health > /dev/null; then
    echo "✓ Frontend: Healthy"
else
    echo "✗ Frontend: Unhealthy"
    EXIT_CODE=1
fi

# Backend API
if curl -sf http://localhost/api/v1/ > /dev/null; then
    echo "✓ Backend API: Healthy"
else
    echo "✗ Backend API: Unhealthy"
    EXIT_CODE=1
fi

# Database
if docker-compose $COMPOSE_FILES exec -T db pg_isready -U jf_manager > /dev/null 2>&1; then
    echo "✓ Database: Healthy"
else
    echo "✗ Database: Unhealthy"
    EXIT_CODE=1
fi

# Redis
if docker-compose $COMPOSE_FILES exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis: Healthy"
else
    echo "✗ Redis: Unhealthy"
    EXIT_CODE=1
fi

echo ""

# Resource usage
echo "Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# Disk usage
echo "Disk Usage:"
df -h / | tail -1
echo ""

# Docker disk usage
echo "Docker Disk Usage:"
docker system df
echo ""

# Check backup age
if [ -d "./backups" ]; then
    LATEST_BACKUP=$(find ./backups -name "backup_*.sql.gz" -type f -printf '%T+ %p\n' | sort -r | head -1 | cut -d' ' -f2-)
    if [ -n "$LATEST_BACKUP" ]; then
        BACKUP_AGE=$(find "$LATEST_BACKUP" -mtime +1 2>/dev/null)
        if [ -n "$BACKUP_AGE" ]; then
            echo "⚠️  Warning: Latest backup is older than 24 hours"
            echo "   Latest backup: $LATEST_BACKUP"
        else
            echo "✓ Backup: Recent (last 24h)"
        fi
    else
        echo "⚠️  Warning: No backups found"
    fi
fi

echo ""
echo "======================================"

exit ${EXIT_CODE:-0}
