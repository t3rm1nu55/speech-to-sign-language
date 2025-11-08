#!/bin/bash

# Quick start script for Speech to Sign Language backend

echo "=========================================="
echo "Speech to Sign Language - Quick Start"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. Please review and update if needed."
fi

# Start services
echo ""
echo "🚀 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if API is running
echo ""
echo "🔍 Checking API health..."
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ API is running!"
else
    echo "❌ API is not responding. Check logs with: docker-compose logs api"
    exit 1
fi

# Initialize database
echo ""
echo "📚 Initializing database with sample data..."
docker-compose exec api python scripts/init_db.py

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "API is running at:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/api/docs"
echo "  - ReDoc: http://localhost:8000/api/redoc"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart"
echo "  - Run tests: python scripts/test_api.py"
echo ""
