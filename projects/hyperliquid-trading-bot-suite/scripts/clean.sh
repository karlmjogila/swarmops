#!/bin/bash

# Cleanup Script
set -e

echo "🧹 Cleaning up development environment..."

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

# Stop and remove containers
echo -e "${YELLOW}Stopping and removing Docker containers...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v || true
echo -e "${GREEN}✓ Stopped containers${NC}"

# Clean Python cache
echo -e "${YELLOW}Cleaning Python cache...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned Python cache${NC}"

# Clean Node.js cache
echo -e "${YELLOW}Cleaning Node.js cache...${NC}"
if [ -d "frontend/node_modules" ]; then
    rm -rf frontend/node_modules
    echo -e "${GREEN}✓ Removed node_modules${NC}"
fi

if [ -d "frontend/.nuxt" ]; then
    rm -rf frontend/.nuxt
    echo -e "${GREEN}✓ Removed .nuxt directory${NC}"
fi

if [ -d "frontend/.output" ]; then
    rm -rf frontend/.output
    echo -e "${GREEN}✓ Removed .output directory${NC}"
fi

# Clean test coverage
echo -e "${YELLOW}Cleaning test coverage...${NC}"
find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name ".coverage" -delete 2>/dev/null || true
find . -type f -name "coverage.xml" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned coverage files${NC}"

# Clean logs
echo -e "${YELLOW}Cleaning logs...${NC}"
if [ -d "logs" ]; then
    rm -rf logs/*
    echo -e "${GREEN}✓ Cleaned log files${NC}"
fi

# Clean temporary files
echo -e "${YELLOW}Cleaning temporary files...${NC}"
find . -type f -name "*.log" -delete 2>/dev/null || true
find . -type f -name "*.tmp" -delete 2>/dev/null || true
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
find . -type f -name "Thumbs.db" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned temporary files${NC}"

# Clean Docker images (optional - commented out to be safe)
# echo -e "${YELLOW}Cleaning Docker images...${NC}"
# docker system prune -f
# echo -e "${GREEN}✓ Cleaned Docker system${NC}"

echo -e "${GREEN}🎉 Cleanup complete!${NC}"
echo -e "${YELLOW}To restart development environment, run: ./scripts/setup-dev.sh${NC}"