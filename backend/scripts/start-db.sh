#!/bin/bash

# PostgreSQL Database Startup Script
# This script starts the PostgreSQL database using Docker Compose

set -e

echo "🚀 Starting PostgreSQL with pgvector..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo ""
    echo "Please start Docker Desktop and try again."
    echo ""
    echo "On macOS:"
    echo "  1. Open Docker Desktop application"
    echo "  2. Wait for Docker to start (whale icon in menu bar)"
    echo "  3. Run this script again"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if .env file exists in backend directory
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "❌ Error: .env file not found in $BACKEND_DIR!"
    echo ""
    echo "Please create a .env file from .env.example in the backend directory."
    echo ""
    echo "Command:"
    echo "  cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
    exit 1
fi

# Change to backend directory
cd "$BACKEND_DIR"

# Start Docker Compose
echo "📦 Starting PostgreSQL container..."
docker-compose up -d

# Wait for database to be ready
echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

# Check health status
if docker-compose ps postgres | grep -q "healthy"; then
    echo ""
    echo "✅ PostgreSQL is running and healthy!"
    echo ""
    echo "📊 Connection Details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: lecture_summarizer_dev"
    echo "  User: postgres"
    echo ""
    echo "🔌 Connect using:"
    echo "  docker-compose exec postgres psql -U postgres -d lecture_summarizer_dev"
    echo ""
    echo "📝 View logs:"
    echo "  docker-compose logs -f postgres"
    echo ""
else
    echo ""
    echo "⚠️  PostgreSQL is starting... (may take a few more seconds)"
    echo ""
    echo "Check status with:"
    echo "  docker-compose ps"
    echo ""
    echo "View logs with:"
    echo "  docker-compose logs postgres"
fi
