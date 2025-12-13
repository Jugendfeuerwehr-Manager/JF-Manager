#!/bin/bash

# Validation script for Docker production setup

set -e

echo "======================================"
echo "JF-Manager Setup Validation"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# Helper functions
check_ok() {
    echo "✓ $1"
}

check_warn() {
    echo "⚠️  $1"
    WARNINGS=$((WARNINGS + 1))
}

check_error() {
    echo "✗ $1"
    ERRORS=$((ERRORS + 1))
}

# 1. Check required files
echo "Checking required files..."
echo ""

FILES=(
    "docker-compose.yml"
    "docker-compose.prod.yml"
    "docker-compose.dev.yml"
    ".env.example"
    "Makefile"
    "setup.sh"
    "deploy.sh"
    "healthcheck.sh"
    "DEPLOYMENT.md"
    "PRODUCTION.md"
    "backend/Dockerfile"
    "backend/.dockerignore"
    "frontend/Dockerfile"
    "frontend/.dockerignore"
    "frontend/nginx.conf"
    "frontend/conf.d/default.conf"
    "scripts/backup.sh"
    "scripts/restore.sh"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        check_ok "$file exists"
    else
        check_error "$file is missing"
    fi
done

echo ""

# 2. Check required directories
echo "Checking required directories..."
echo ""

DIRS=(
    "frontend/conf.d/locations"
    "nginx/ssl"
    "backups"
    "scripts"
    "systemd"
    ".github/workflows"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_ok "$dir/ exists"
    else
        check_error "$dir/ is missing"
    fi
done

echo ""

# 3. Check file permissions
echo "Checking file permissions..."
echo ""

EXECUTABLE_FILES=(
    "setup.sh"
    "deploy.sh"
    "healthcheck.sh"
    "scripts/backup.sh"
    "scripts/restore.sh"
)

for file in "${EXECUTABLE_FILES[@]}"; do
    if [ -x "$file" ]; then
        check_ok "$file is executable"
    else
        check_warn "$file is not executable (run: chmod +x $file)"
    fi
done

echo ""

# 4. Check environment configuration
echo "Checking environment configuration..."
echo ""

if [ -f ".env" ]; then
    check_ok ".env file exists"
    
    # Check for placeholder values
    if grep -q "CHANGE_ME" .env 2>/dev/null; then
        check_warn ".env contains placeholder values (CHANGE_ME)"
    else
        check_ok ".env appears configured"
    fi
    
    # Check file permissions
    PERMS=$(stat -f "%OLp" .env 2>/dev/null || stat -c "%a" .env 2>/dev/null)
    if [ "$PERMS" = "600" ]; then
        check_ok ".env has correct permissions (600)"
    else
        check_warn ".env permissions are $PERMS (should be 600)"
    fi
else
    check_warn ".env file not found (copy from .env.example)"
fi

echo ""

# 5. Check Docker installation
echo "Checking Docker installation..."
echo ""

if command -v docker &> /dev/null; then
    check_ok "Docker is installed"
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo "   Version: $DOCKER_VERSION"
else
    check_error "Docker is not installed"
fi

if command -v docker-compose &> /dev/null; then
    check_ok "Docker Compose is installed"
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    echo "   Version: $COMPOSE_VERSION"
else
    check_error "Docker Compose is not installed"
fi

if docker info &> /dev/null; then
    check_ok "Docker daemon is running"
else
    check_error "Docker daemon is not running"
fi

echo ""

# 6. Check Dockerfile syntax
echo "Checking Dockerfile syntax..."
echo ""

if docker run --rm -i hadolint/hadolint < backend/Dockerfile > /dev/null 2>&1; then
    check_ok "Backend Dockerfile syntax is valid"
else
    check_warn "Backend Dockerfile has linting warnings (install hadolint for details)"
fi

if docker run --rm -i hadolint/hadolint < frontend/Dockerfile > /dev/null 2>&1; then
    check_ok "Frontend Dockerfile syntax is valid"
else
    check_warn "Frontend Dockerfile has linting warnings (install hadolint for details)"
fi

echo ""

# 7. Check docker-compose syntax
echo "Checking docker-compose syntax..."
echo ""

if docker-compose config > /dev/null 2>&1; then
    check_ok "docker-compose.yml syntax is valid"
else
    check_error "docker-compose.yml has syntax errors"
fi

echo ""

# 8. Check Nginx configuration syntax
echo "Checking Nginx configuration..."
echo ""

# Check if nginx conf files have basic syntax
for conf in frontend/conf.d/*.conf frontend/conf.d/locations/*.conf; do
    if [ -f "$conf" ]; then
        if grep -q "location" "$conf" || grep -q "server" "$conf" || grep -q "upstream" "$conf"; then
            check_ok "$(basename $conf) appears valid"
        else
            check_warn "$(basename $conf) may have issues"
        fi
    fi
done

echo ""

# 9. Check network ports
echo "Checking network ports..."
echo ""

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        check_warn "Port $1 is already in use"
    else
        check_ok "Port $1 is available"
    fi
}

check_port 80
check_port 443
check_port 8000
check_port 5432
check_port 6379

echo ""

# 10. Check system resources
echo "Checking system resources..."
echo ""

# Check available disk space
DISK_AVAIL=$(df -h . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "${DISK_AVAIL%%.*}" -gt 10 ]; then
    check_ok "Sufficient disk space available (${DISK_AVAIL}GB free)"
else
    check_warn "Low disk space (${DISK_AVAIL}GB free, recommend >10GB)"
fi

# Check available memory
if command -v free &> /dev/null; then
    MEM_AVAIL=$(free -g | grep Mem | awk '{print $7}')
    if [ "$MEM_AVAIL" -gt 2 ]; then
        check_ok "Sufficient memory available (${MEM_AVAIL}GB free)"
    else
        check_warn "Low memory (${MEM_AVAIL}GB free, recommend >2GB)"
    fi
fi

echo ""

# Summary
echo "======================================"
echo "Validation Summary"
echo "======================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed! Ready for deployment."
    echo ""
    echo "Next steps:"
    echo "  1. Review and update .env file"
    echo "  2. Run: ./setup.sh  OR  ./deploy.sh"
    echo "  3. Access: http://localhost"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  $WARNINGS warning(s) found."
    echo "Review the warnings above, but you can proceed with deployment."
    echo ""
    echo "To deploy: ./setup.sh  OR  ./deploy.sh"
    exit 0
else
    echo "❌ $ERRORS error(s) and $WARNINGS warning(s) found."
    echo "Please fix the errors above before deploying."
    exit 1
fi
