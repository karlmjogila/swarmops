#!/bin/bash

# Hyperliquid Trading Bot Suite - Development Setup Script

set -e

echo "🚀 Setting up Hyperliquid Trading Bot Suite development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python 3.11+
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.11+ is required but not found"
        exit 1
    fi
    
    # Check Node.js
    if command -v node >/dev/null 2>&1; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION found"
    else
        print_error "Node.js 18+ is required but not found"
        exit 1
    fi
    
    # Check Docker
    if command -v docker >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker found: $DOCKER_VERSION"
    else
        print_warning "Docker not found - you'll need it for database services"
    fi
    
    # Check Docker Compose
    if command -v docker-compose >/dev/null 2>&1; then
        print_success "Docker Compose found"
    else
        print_warning "Docker Compose not found - you'll need it for database services"
    fi
}

# Create environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        print_success "Created .env from template"
        print_warning "⚠️  Please update .env with your configuration:"
        print_warning "   - Database connection string"
        print_warning "   - API keys (Anthropic/OpenAI)"
        print_warning "   - Hyperliquid credentials"
        print_warning "   - Redis connection"
    else
        print_warning ".env already exists - skipping"
    fi
}

# Setup backend
setup_backend() {
    print_status "Setting up Python backend..."
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -e .
    
    print_success "Backend dependencies installed"
    
    cd ..
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    print_success "Frontend dependencies installed"
    
    cd ..
}

# Setup databases
setup_databases() {
    print_status "Setting up database services..."
    
    if command -v docker-compose >/dev/null 2>&1; then
        # Start database services
        print_status "Starting PostgreSQL and Redis..."
        docker-compose up -d postgres redis
        
        # Wait for services
        print_status "Waiting for services to be ready..."
        sleep 10
        
        # Run database migrations
        print_status "Running database migrations..."
        cd backend
        source venv/bin/activate
        
        # Check if alembic is installed
        if command -v alembic >/dev/null 2>&1; then
            alembic upgrade head
            print_success "Database migrations completed"
        else
            print_warning "Alembic not found - run migrations manually with: 'alembic upgrade head'"
        fi
        
        cd ..
        
        print_success "Database services are running"
    else
        print_warning "Docker Compose not available - please set up PostgreSQL and Redis manually"
    fi
}

# Create directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p uploads
    mkdir -p temp
    mkdir -p logs
    mkdir -p data
    
    print_success "Directories created"
}

# Main setup function
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         Hyperliquid Trading Bot Suite - Dev Setup           ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_prerequisites
    setup_environment
    create_directories
    setup_backend
    setup_frontend
    setup_databases
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                      Setup Complete! 🎉                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    print_success "Development environment is ready!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Update .env with your configuration"
    echo "   2. Start development servers:"
    echo "      • Backend:  make backend  (or cd backend && uvicorn src.api.main:app --reload)"
    echo "      • Frontend: make frontend (or cd frontend && npm run dev)"
    echo "   3. Access the application:"
    echo "      • Frontend: http://localhost:3000"
    echo "      • Backend API: http://localhost:8000"
    echo "      • API Docs: http://localhost:8000/docs"
    echo ""
    echo "🛠️  Useful commands:"
    echo "   • make help       - Show all available commands"
    echo "   • make dev        - Start both servers"
    echo "   • make test       - Run all tests"
    echo "   • make lint       - Run code quality checks"
    echo ""
    print_warning "⚠️  Remember to configure your environment variables in .env"
}

# Run main function
main "$@"