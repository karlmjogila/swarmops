#!/bin/bash

# Development Environment Setup Script
set -e

echo "🚀 Setting up Hyperliquid Trading Bot Suite development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites found${NC}"

# Copy environment files
echo -e "${YELLOW}Setting up environment files...${NC}"

if [ ! -f ".env" ]; then
    cp .env.development .env
    echo -e "${GREEN}✓ Created .env from .env.development${NC}"
else
    echo -e "${YELLOW}ℹ .env already exists, skipping${NC}"
fi

# Set up backend
echo -e "${YELLOW}Setting up backend...${NC}"
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Created Python virtual environment${NC}"
fi

source venv/bin/activate
pip install -e .
echo -e "${GREEN}✓ Installed backend dependencies${NC}"

cd ..

# Set up frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
    npm install
    echo -e "${GREEN}✓ Installed frontend dependencies${NC}"
else
    echo -e "${YELLOW}ℹ node_modules already exists, running npm ci${NC}"
    npm ci
fi

cd ..

# Set up pre-commit hooks
echo -e "${YELLOW}Setting up pre-commit hooks...${NC}"
if command_exists pre-commit; then
    pre-commit install
    echo -e "${GREEN}✓ Installed pre-commit hooks${NC}"
else
    echo -e "${YELLOW}ℹ pre-commit not installed, skipping hooks setup${NC}"
fi

# Start services
echo -e "${YELLOW}Starting development services...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis
echo -e "${GREEN}✓ Started database services${NC}"

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Run database migrations (if they exist)
echo -e "${YELLOW}Running database migrations...${NC}"
if [ -f "backend/alembic.ini" ]; then
    cd backend
    source venv/bin/activate
    alembic upgrade head || echo -e "${YELLOW}ℹ No migrations to run or alembic not set up yet${NC}"
    cd ..
fi

echo -e "${GREEN}🎉 Development environment setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update .env with your API keys and configuration"
echo "2. Run 'make dev' to start the development servers"
echo "3. Visit http://localhost:3000 for the frontend"
echo "4. Visit http://localhost:8000/docs for the API documentation"