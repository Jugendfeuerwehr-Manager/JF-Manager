#!/bin/bash

set -e

echo "======================================"
echo "JF-Manager Production Setup"
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker is installed"
echo "✓ Docker Compose is installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate random passwords
    POSTGRES_PW=$(openssl rand -base64 32)
    DJANGO_SECRET=$(openssl rand -base64 50)
    ADMIN_PW=$(openssl rand -base64 16)
    
    # Update .env with generated passwords (macOS compatible)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|POSTGRES_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD|POSTGRES_PASSWORD=$POSTGRES_PW|g" .env
        sed -i '' "s|DJANGO_SECRET_KEY=CHANGE_ME_TO_RANDOM_50_CHARS|DJANGO_SECRET_KEY=$DJANGO_SECRET|g" .env
        sed -i '' "s|DJANGO_ADMIN_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD|DJANGO_ADMIN_PASSWORD=$ADMIN_PW|g" .env
    else
        sed -i "s|POSTGRES_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD|POSTGRES_PASSWORD=$POSTGRES_PW|g" .env
        sed -i "s|DJANGO_SECRET_KEY=CHANGE_ME_TO_RANDOM_50_CHARS|DJANGO_SECRET_KEY=$DJANGO_SECRET|g" .env
        sed -i "s|DJANGO_ADMIN_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD|DJANGO_ADMIN_PASSWORD=$ADMIN_PW|g" .env
    fi
    
    echo "✓ .env file created with random passwords"
    echo ""
    echo "⚠️  IMPORTANT: Please review and update .env file with:"
    echo "   - Your domain name (ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS)"
    echo "   - Email configuration"
    echo "   - Admin email address"
    echo ""
    echo "Admin password: $ADMIN_PW"
    echo ""
    read -p "Press Enter to continue after updating .env file..."
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check health
echo ""
echo "Checking service health..."
docker-compose ps

echo ""
echo "======================================"
echo "✓ JF-Manager Setup Complete!"
echo "======================================"
echo ""
echo "Access your application at:"
echo "  Frontend: http://localhost"
echo "  Admin:    http://localhost/admin"
echo "  API:      http://localhost/api/v1/"
echo ""
echo "Useful commands:"
echo "  make logs          - View logs"
echo "  make backup        - Create backup"
echo "  make help          - Show all commands"
echo ""
echo "Next steps:"
echo "  1. Configure SSL certificates (see DEPLOYMENT.md)"
echo "  2. Set up automated backups"
echo "  3. Configure your domain name"
echo ""
